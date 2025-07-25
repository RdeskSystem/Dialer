import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import random
import statistics

from src.models import db, Campaign, Lead, Call, User, CampaignAssignment, AgentPerformance
from src.services.sip_service import sip_service

logger = logging.getLogger(__name__)

class DialerMode(Enum):
    MANUAL = "manual"
    TURBO = "turbo"
    PREDICTIVE = "predictive"

@dataclass
class DialerStats:
    """Statistics for dialer performance tracking"""
    total_calls: int = 0
    answered_calls: int = 0
    busy_calls: int = 0
    no_answer_calls: int = 0
    failed_calls: int = 0
    average_call_duration: float = 0.0
    answer_rate: float = 0.0
    agent_utilization: float = 0.0

@dataclass
class AgentStatus:
    """Agent status tracking"""
    agent_id: int
    status: str  # 'available', 'busy', 'on_call', 'offline'
    current_call_id: Optional[int] = None
    last_call_end: Optional[datetime] = None
    calls_today: int = 0
    talk_time_today: int = 0  # seconds

class DialerService:
    """Service for managing different dialing modes and algorithms"""
    
    def __init__(self):
        self.active_campaigns = {}  # campaign_id -> dialer instance
        self.agent_statuses = {}  # agent_id -> AgentStatus
        self.dialer_stats = {}  # campaign_id -> DialerStats
        self.running = False
        self.thread = None
        
    def start_campaign_dialer(self, campaign_id: int) -> bool:
        """Start dialer for a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return False
            
            if campaign_id in self.active_campaigns:
                logger.warning(f"Dialer already running for campaign {campaign_id}")
                return True
            
            # Create appropriate dialer based on campaign mode
            if campaign.dialer_mode == DialerMode.MANUAL.value:
                dialer = ManualDialer(campaign_id, self)
            elif campaign.dialer_mode == DialerMode.TURBO.value:
                dialer = TurboDialer(campaign_id, self)
            elif campaign.dialer_mode == DialerMode.PREDICTIVE.value:
                dialer = PredictiveDialer(campaign_id, self)
            else:
                logger.error(f"Unknown dialer mode: {campaign.dialer_mode}")
                return False
            
            self.active_campaigns[campaign_id] = dialer
            self.dialer_stats[campaign_id] = DialerStats()
            
            # Start dialer
            dialer.start()
            
            logger.info(f"Started {campaign.dialer_mode} dialer for campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start dialer for campaign {campaign_id}: {e}")
            return False
    
    def stop_campaign_dialer(self, campaign_id: int) -> bool:
        """Stop dialer for a campaign"""
        try:
            if campaign_id not in self.active_campaigns:
                return True
            
            dialer = self.active_campaigns[campaign_id]
            dialer.stop()
            
            del self.active_campaigns[campaign_id]
            
            logger.info(f"Stopped dialer for campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop dialer for campaign {campaign_id}: {e}")
            return False
    
    def update_agent_status(self, agent_id: int, status: str, call_id: Optional[int] = None):
        """Update agent status"""
        if agent_id not in self.agent_statuses:
            self.agent_statuses[agent_id] = AgentStatus(agent_id=agent_id, status=status)
        else:
            self.agent_statuses[agent_id].status = status
            
        if call_id:
            self.agent_statuses[agent_id].current_call_id = call_id
        elif status == 'available':
            self.agent_statuses[agent_id].current_call_id = None
            self.agent_statuses[agent_id].last_call_end = datetime.utcnow()
    
    def get_available_agents(self, campaign_id: int) -> List[int]:
        """Get list of available agents for a campaign"""
        # Get agents assigned to campaign
        assignments = CampaignAssignment.query.filter_by(campaign_id=campaign_id).all()
        assigned_agent_ids = [a.user_id for a in assignments]
        
        # Filter by availability
        available_agents = []
        for agent_id in assigned_agent_ids:
            if agent_id in self.agent_statuses:
                if self.agent_statuses[agent_id].status == 'available':
                    available_agents.append(agent_id)
            else:
                # Agent not tracked yet, assume available
                self.agent_statuses[agent_id] = AgentStatus(agent_id=agent_id, status='available')
                available_agents.append(agent_id)
        
        return available_agents
    
    def get_next_lead(self, campaign_id: int) -> Optional[Lead]:
        """Get next lead to call for a campaign"""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return None
        
        # Get leads that haven't reached max attempts
        leads = db.session.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status.in_(['new', 'callback', 'interested']),
            Lead.phone_number.isnot(None)
        ).all()
        
        # Filter leads by attempt count
        valid_leads = []
        for lead in leads:
            call_count = Call.query.filter_by(lead_id=lead.id).count()
            if call_count < campaign.max_attempts:
                # Check retry delay for previously called leads
                if call_count > 0:
                    last_call = Call.query.filter_by(lead_id=lead.id).order_by(Call.started_at.desc()).first()
                    if last_call:
                        retry_time = last_call.started_at + timedelta(minutes=campaign.retry_delay_minutes)
                        if datetime.utcnow() < retry_time:
                            continue
                
                valid_leads.append(lead)
        
        # Return first valid lead (could be enhanced with prioritization)
        return valid_leads[0] if valid_leads else None
    
    def initiate_call(self, campaign_id: int, lead_id: int, agent_id: int) -> Optional[int]:
        """Initiate a call through the dialer service"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return None
            
            # Create call record
            call = Call(
                lead_id=lead_id,
                campaign_id=campaign_id,
                agent_id=agent_id,
                phone_number=lead.phone_number,
                call_direction='outbound',
                call_status='initiated'
            )
            
            db.session.add(call)
            db.session.flush()
            
            # Update agent status
            self.update_agent_status(agent_id, 'on_call', call.id)
            
            # Initiate call through SIP service
            agent_channel = f"Agent/{agent_id}"
            if sip_service.originate_call(lead.phone_number, agent_channel, call.id):
                db.session.commit()
                
                # Update lead last contacted time
                lead.last_contacted = datetime.utcnow()
                db.session.commit()
                
                # Update statistics
                if campaign_id in self.dialer_stats:
                    self.dialer_stats[campaign_id].total_calls += 1
                
                return call.id
            else:
                # Call initiation failed
                call.call_status = 'failed'
                db.session.commit()
                
                # Update agent status back to available
                self.update_agent_status(agent_id, 'available')
                
                return None
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to initiate call: {e}")
            return None
    
    def get_campaign_stats(self, campaign_id: int) -> Optional[DialerStats]:
        """Get statistics for a campaign"""
        return self.dialer_stats.get(campaign_id)
    
    def get_agent_status(self, agent_id: int) -> Optional[AgentStatus]:
        """Get status for an agent"""
        return self.agent_statuses.get(agent_id)

class BaseDialer:
    """Base class for all dialer implementations"""
    
    def __init__(self, campaign_id: int, dialer_service: DialerService):
        self.campaign_id = campaign_id
        self.dialer_service = dialer_service
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the dialer"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the dialer"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _run(self):
        """Main dialer loop - to be implemented by subclasses"""
        raise NotImplementedError

class ManualDialer(BaseDialer):
    """Manual dialer - agents manually select leads to call"""
    
    def _run(self):
        """Manual dialer doesn't have an automated loop"""
        logger.info(f"Manual dialer started for campaign {self.campaign_id}")
        
        while self.running:
            # Manual dialer just waits - calls are initiated through API
            time.sleep(1)
        
        logger.info(f"Manual dialer stopped for campaign {self.campaign_id}")
    
    def manual_call(self, lead_id: int, agent_id: int) -> Optional[int]:
        """Manually initiate a call"""
        return self.dialer_service.initiate_call(self.campaign_id, lead_id, agent_id)

class TurboDialer(BaseDialer):
    """Turbo dialer - sequential batch dialing with auto-skip for failed connections"""
    
    def _run(self):
        """Turbo dialer main loop"""
        logger.info(f"Turbo dialer started for campaign {self.campaign_id}")
        
        campaign = Campaign.query.get(self.campaign_id)
        if not campaign:
            return
        
        delay_seconds = campaign.turbo_delay_seconds or 5
        
        while self.running:
            try:
                # Get available agents
                available_agents = self.dialer_service.get_available_agents(self.campaign_id)
                
                if available_agents:
                    # Get next lead
                    lead = self.dialer_service.get_next_lead(self.campaign_id)
                    
                    if lead:
                        # Select first available agent
                        agent_id = available_agents[0]
                        
                        # Initiate call
                        call_id = self.dialer_service.initiate_call(self.campaign_id, lead.id, agent_id)
                        
                        if call_id:
                            logger.info(f"Turbo dialer initiated call {call_id} for lead {lead.id} to agent {agent_id}")
                        else:
                            logger.warning(f"Turbo dialer failed to initiate call for lead {lead.id}")
                    else:
                        # No leads available, wait longer
                        time.sleep(30)
                        continue
                
                # Wait before next attempt
                time.sleep(delay_seconds)
                
            except Exception as e:
                logger.error(f"Error in turbo dialer for campaign {self.campaign_id}: {e}")
                time.sleep(10)
        
        logger.info(f"Turbo dialer stopped for campaign {self.campaign_id}")

class PredictiveDialer(BaseDialer):
    """Predictive dialer - smart algorithm predicts agent availability and call pickup probability"""
    
    def __init__(self, campaign_id: int, dialer_service: DialerService):
        super().__init__(campaign_id, dialer_service)
        self.call_history = []  # Recent call outcomes for prediction
        self.agent_performance = {}  # agent_id -> performance metrics
        
    def _run(self):
        """Predictive dialer main loop"""
        logger.info(f"Predictive dialer started for campaign {self.campaign_id}")
        
        campaign = Campaign.query.get(self.campaign_id)
        if not campaign:
            return
        
        predictive_ratio = campaign.predictive_ratio or 1.2
        
        while self.running:
            try:
                # Update call history and agent performance
                self._update_metrics()
                
                # Get available agents
                available_agents = self.dialer_service.get_available_agents(self.campaign_id)
                
                if available_agents:
                    # Calculate how many calls to make based on prediction
                    calls_to_make = self._calculate_calls_needed(available_agents, predictive_ratio)
                    
                    for _ in range(calls_to_make):
                        if not self.running:
                            break
                        
                        # Get next lead
                        lead = self.dialer_service.get_next_lead(self.campaign_id)
                        
                        if lead:
                            # Select best agent based on performance
                            agent_id = self._select_best_agent(available_agents)
                            
                            # Initiate call
                            call_id = self.dialer_service.initiate_call(self.campaign_id, lead.id, agent_id)
                            
                            if call_id:
                                logger.info(f"Predictive dialer initiated call {call_id} for lead {lead.id} to agent {agent_id}")
                                # Remove agent from available list for this round
                                if agent_id in available_agents:
                                    available_agents.remove(agent_id)
                            else:
                                logger.warning(f"Predictive dialer failed to initiate call for lead {lead.id}")
                        else:
                            break
                
                # Wait before next prediction cycle
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in predictive dialer for campaign {self.campaign_id}: {e}")
                time.sleep(15)
        
        logger.info(f"Predictive dialer stopped for campaign {self.campaign_id}")
    
    def _update_metrics(self):
        """Update call history and agent performance metrics"""
        try:
            # Get recent calls (last 100)
            recent_calls = Call.query.filter(
                Call.campaign_id == self.campaign_id,
                Call.started_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(Call.started_at.desc()).limit(100).all()
            
            # Update call history for answer rate prediction
            self.call_history = []
            for call in recent_calls:
                outcome = 'answered' if call.call_status == 'answered' else 'not_answered'
                self.call_history.append({
                    'outcome': outcome,
                    'duration': call.duration_seconds or 0,
                    'timestamp': call.started_at
                })
            
            # Update agent performance
            for agent_id in self.dialer_service.get_available_agents(self.campaign_id):
                agent_calls = [c for c in recent_calls if c.agent_id == agent_id]
                
                if agent_calls:
                    answered_calls = [c for c in agent_calls if c.call_status == 'answered']
                    total_talk_time = sum([c.duration_seconds or 0 for c in answered_calls])
                    
                    self.agent_performance[agent_id] = {
                        'total_calls': len(agent_calls),
                        'answered_calls': len(answered_calls),
                        'answer_rate': len(answered_calls) / len(agent_calls) if agent_calls else 0,
                        'average_call_duration': total_talk_time / len(answered_calls) if answered_calls else 0,
                        'total_talk_time': total_talk_time
                    }
                else:
                    # Default performance for agents without recent calls
                    self.agent_performance[agent_id] = {
                        'total_calls': 0,
                        'answered_calls': 0,
                        'answer_rate': 0.3,  # Default assumption
                        'average_call_duration': 180,  # 3 minutes default
                        'total_talk_time': 0
                    }
                    
        except Exception as e:
            logger.error(f"Error updating predictive dialer metrics: {e}")
    
    def _calculate_calls_needed(self, available_agents: List[int], predictive_ratio: float) -> int:
        """Calculate how many calls to initiate based on prediction algorithm"""
        if not available_agents:
            return 0
        
        # Calculate expected answer rate from recent history
        if self.call_history:
            answered_count = len([c for c in self.call_history if c['outcome'] == 'answered'])
            answer_rate = answered_count / len(self.call_history)
        else:
            answer_rate = 0.3  # Default assumption
        
        # Calculate average call duration
        answered_calls = [c for c in self.call_history if c['outcome'] == 'answered' and c['duration'] > 0]
        if answered_calls:
            avg_call_duration = statistics.mean([c['duration'] for c in answered_calls])
        else:
            avg_call_duration = 180  # 3 minutes default
        
        # Predict how many agents will be free soon
        agents_becoming_free = self._predict_agents_becoming_free(avg_call_duration)
        
        # Total agents to consider
        total_agents = len(available_agents) + agents_becoming_free
        
        # Calculate calls needed based on predictive ratio and answer rate
        calls_needed = int(total_agents * predictive_ratio / answer_rate)
        
        # Cap at reasonable limits
        max_calls = min(len(available_agents) * 3, 10)  # Don't overwhelm
        calls_needed = min(calls_needed, max_calls)
        
        logger.debug(f"Predictive calculation: {len(available_agents)} available agents, "
                    f"{answer_rate:.2f} answer rate, {calls_needed} calls needed")
        
        return max(0, calls_needed)
    
    def _predict_agents_becoming_free(self, avg_call_duration: float) -> int:
        """Predict how many agents will become free in the next few minutes"""
        agents_becoming_free = 0
        current_time = datetime.utcnow()
        
        for agent_id, status in self.dialer_service.agent_statuses.items():
            if status.status == 'on_call' and status.current_call_id:
                # Get call start time
                call = Call.query.get(status.current_call_id)
                if call and call.started_at:
                    call_duration = (current_time - call.started_at).total_seconds()
                    
                    # If call is approaching average duration, agent might become free soon
                    if call_duration >= avg_call_duration * 0.8:
                        agents_becoming_free += 1
        
        return agents_becoming_free
    
    def _select_best_agent(self, available_agents: List[int]) -> int:
        """Select the best agent based on performance metrics"""
        if len(available_agents) == 1:
            return available_agents[0]
        
        # Score agents based on performance
        agent_scores = {}
        
        for agent_id in available_agents:
            performance = self.agent_performance.get(agent_id, {})
            
            # Calculate score based on multiple factors
            answer_rate = performance.get('answer_rate', 0.3)
            total_calls = performance.get('total_calls', 0)
            
            # Prefer agents with higher answer rates and some experience
            score = answer_rate * 0.7 + min(total_calls / 10, 1.0) * 0.3
            
            # Add some randomness to avoid always picking the same agent
            score += random.uniform(-0.1, 0.1)
            
            agent_scores[agent_id] = score
        
        # Return agent with highest score
        best_agent = max(agent_scores.keys(), key=lambda x: agent_scores[x])
        return best_agent

# Global dialer service instance
dialer_service = DialerService()


from src.models.user import db
from datetime import datetime
import json

class Call(db.Model):
    __tablename__ = 'calls'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    phone_number = db.Column(db.String(20), nullable=False)
    call_direction = db.Column(db.String(10), default='outbound')
    call_status = db.Column(db.String(20), nullable=False)
    call_outcome = db.Column(db.String(30))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    recording_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    disposition_code = db.Column(db.String(10))
    next_action = db.Column(db.String(50))
    next_contact_date = db.Column(db.DateTime)
    
    # Relationships
    events = db.relationship('CallEvent', backref='call', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Call {self.id} - {self.phone_number} ({self.call_status})>'
    
    def get_duration_formatted(self):
        """Get call duration in MM:SS format"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    def calculate_duration(self):
        """Calculate and set duration based on start and end times"""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'campaign_id': self.campaign_id,
            'agent_id': self.agent_id,
            'phone_number': self.phone_number,
            'call_direction': self.call_direction,
            'call_status': self.call_status,
            'call_outcome': self.call_outcome,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.duration_seconds,
            'duration_formatted': self.get_duration_formatted(),
            'recording_url': self.recording_url,
            'notes': self.notes,
            'disposition_code': self.disposition_code,
            'next_action': self.next_action,
            'next_contact_date': self.next_contact_date.isoformat() if self.next_contact_date else None
        }

class CallEvent(db.Model):
    __tablename__ = 'call_events'
    
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('calls.id'), nullable=False)
    event_type = db.Column(db.String(30), nullable=False)
    event_data = db.Column(db.Text)  # JSON string for flexible event data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CallEvent {self.event_type} for Call {self.call_id}>'
    
    def get_event_data(self):
        """Parse event data JSON"""
        if self.event_data:
            try:
                return json.loads(self.event_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_event_data(self, data_dict):
        """Set event data as JSON"""
        self.event_data = json.dumps(data_dict) if data_dict else None
    
    def to_dict(self):
        return {
            'id': self.id,
            'call_id': self.call_id,
            'event_type': self.event_type,
            'event_data': self.get_event_data(),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class AgentPerformance(db.Model):
    __tablename__ = 'agent_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    calls_made = db.Column(db.Integer, default=0)
    calls_answered = db.Column(db.Integer, default=0)
    total_talk_time = db.Column(db.Integer, default=0)  # in seconds
    conversions = db.Column(db.Integer, default=0)
    login_time = db.Column(db.Integer, default=0)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint for agent, campaign, and date
    __table_args__ = (db.UniqueConstraint('agent_id', 'campaign_id', 'date', name='unique_agent_campaign_date'),)
    
    def __repr__(self):
        return f'<AgentPerformance Agent:{self.agent_id} Campaign:{self.campaign_id} Date:{self.date}>'
    
    def get_talk_time_formatted(self):
        """Get talk time in HH:MM:SS format"""
        if self.total_talk_time:
            hours = self.total_talk_time // 3600
            minutes = (self.total_talk_time % 3600) // 60
            seconds = self.total_talk_time % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    def get_login_time_formatted(self):
        """Get login time in HH:MM:SS format"""
        if self.login_time:
            hours = self.login_time // 3600
            minutes = (self.login_time % 3600) // 60
            seconds = self.login_time % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'campaign_id': self.campaign_id,
            'date': self.date.isoformat() if self.date else None,
            'calls_made': self.calls_made,
            'calls_answered': self.calls_answered,
            'total_talk_time': self.total_talk_time,
            'talk_time_formatted': self.get_talk_time_formatted(),
            'conversions': self.conversions,
            'login_time': self.login_time,
            'login_time_formatted': self.get_login_time_formatted(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'answer_rate': self.calls_answered / self.calls_made if self.calls_made > 0 else 0,
            'conversion_rate': self.conversions / self.calls_answered if self.calls_answered > 0 else 0
        }


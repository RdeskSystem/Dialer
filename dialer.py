from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from src.models import db, Campaign, Lead, CampaignAssignment
from src.services.dialer_service import dialer_service, DialerMode

dialer_bp = Blueprint('dialer', __name__)

def require_role(allowed_roles):
    """Decorator to check user role"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role not in allowed_roles:
                return jsonify({'error': {'code': 'INSUFFICIENT_PERMISSIONS', 'message': 'Insufficient permissions'}}), 403
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@dialer_bp.route('/dialer/campaigns/<int:campaign_id>/start', methods=['POST'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def start_campaign_dialer(campaign_id):
    """Start dialer for a campaign"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Check if campaign is active
        if campaign.status != 'active':
            return jsonify({'error': {'code': 'CAMPAIGN_NOT_ACTIVE', 'message': 'Campaign must be active to start dialer'}}), 400
        
        # Check if campaign has assigned agents
        assignments = CampaignAssignment.query.filter_by(campaign_id=campaign_id).count()
        if assignments == 0:
            return jsonify({'error': {'code': 'NO_AGENTS_ASSIGNED', 'message': 'No agents assigned to campaign'}}), 400
        
        # Check if campaign has leads
        leads_count = Lead.query.filter_by(campaign_id=campaign_id).count()
        if leads_count == 0:
            return jsonify({'error': {'code': 'NO_LEADS_AVAILABLE', 'message': 'No leads available in campaign'}}), 400
        
        # Start dialer
        if dialer_service.start_campaign_dialer(campaign_id):
            return jsonify({
                'message': f'{campaign.dialer_mode.title()} dialer started successfully',
                'campaign_id': campaign_id,
                'dialer_mode': campaign.dialer_mode,
                'started_at': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': {'code': 'DIALER_START_FAILED', 'message': 'Failed to start dialer'}}), 500
            
    except Exception as e:
        return jsonify({'error': {'code': 'START_DIALER_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/campaigns/<int:campaign_id>/stop', methods=['POST'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def stop_campaign_dialer(campaign_id):
    """Stop dialer for a campaign"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Stop dialer
        if dialer_service.stop_campaign_dialer(campaign_id):
            return jsonify({
                'message': f'{campaign.dialer_mode.title()} dialer stopped successfully',
                'campaign_id': campaign_id,
                'stopped_at': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': {'code': 'DIALER_STOP_FAILED', 'message': 'Failed to stop dialer'}}), 500
            
    except Exception as e:
        return jsonify({'error': {'code': 'STOP_DIALER_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/campaigns/<int:campaign_id>/status', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor', 'agent'])
def get_dialer_status(campaign_id):
    """Get dialer status for a campaign"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_role = claims.get('role')
        
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Check if agent has access to this campaign
        if user_role == 'agent':
            assignment = CampaignAssignment.query.filter_by(
                campaign_id=campaign_id,
                user_id=current_user_id
            ).first()
            
            if not assignment:
                return jsonify({'error': {'code': 'ACCESS_DENIED', 'message': 'Access denied to this campaign'}}), 403
        
        # Check if dialer is running
        is_running = campaign_id in dialer_service.active_campaigns
        
        # Get dialer statistics
        stats = dialer_service.get_campaign_stats(campaign_id)
        
        # Get available agents
        available_agents = dialer_service.get_available_agents(campaign_id)
        
        # Get agent statuses
        agent_statuses = {}
        assignments = CampaignAssignment.query.filter_by(campaign_id=campaign_id).all()
        for assignment in assignments:
            agent_status = dialer_service.get_agent_status(assignment.user_id)
            if agent_status:
                agent_statuses[assignment.user_id] = {
                    'status': agent_status.status,
                    'current_call_id': agent_status.current_call_id,
                    'calls_today': agent_status.calls_today,
                    'talk_time_today': agent_status.talk_time_today
                }
            else:
                agent_statuses[assignment.user_id] = {
                    'status': 'offline',
                    'current_call_id': None,
                    'calls_today': 0,
                    'talk_time_today': 0
                }
        
        response = {
            'campaign_id': campaign_id,
            'dialer_mode': campaign.dialer_mode,
            'is_running': is_running,
            'available_agents_count': len(available_agents),
            'agent_statuses': agent_statuses
        }
        
        if stats:
            response['statistics'] = {
                'total_calls': stats.total_calls,
                'answered_calls': stats.answered_calls,
                'busy_calls': stats.busy_calls,
                'no_answer_calls': stats.no_answer_calls,
                'failed_calls': stats.failed_calls,
                'answer_rate': stats.answer_rate,
                'average_call_duration': stats.average_call_duration,
                'agent_utilization': stats.agent_utilization
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_DIALER_STATUS_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/manual-call', methods=['POST'])
@jwt_required()
def manual_call():
    """Initiate a manual call (for manual dialer mode)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('lead_id') or not data.get('campaign_id'):
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'lead_id and campaign_id are required'}}), 400
        
        lead_id = data.get('lead_id')
        campaign_id = data.get('campaign_id')
        
        # Verify campaign exists and is in manual mode
        campaign = Campaign.query.get_or_404(campaign_id)
        if campaign.dialer_mode != DialerMode.MANUAL.value:
            return jsonify({'error': {'code': 'INVALID_DIALER_MODE', 'message': 'Campaign is not in manual dialer mode'}}), 400
        
        # Verify lead exists and belongs to campaign
        lead = Lead.query.filter_by(id=lead_id, campaign_id=campaign_id).first()
        if not lead:
            return jsonify({'error': {'code': 'LEAD_NOT_FOUND', 'message': 'Lead not found in specified campaign'}}), 404
        
        # Check if user is assigned to campaign (for agents)
        claims = get_jwt()
        user_role = claims.get('role')
        if user_role == 'agent':
            assignment = CampaignAssignment.query.filter_by(
                campaign_id=campaign_id,
                user_id=current_user_id
            ).first()
            if not assignment:
                return jsonify({'error': {'code': 'ACCESS_DENIED', 'message': 'Not assigned to this campaign'}}), 403
        
        # Check if agent is available
        agent_status = dialer_service.get_agent_status(current_user_id)
        if agent_status and agent_status.status != 'available':
            return jsonify({'error': {'code': 'AGENT_NOT_AVAILABLE', 'message': f'Agent status is {agent_status.status}'}}), 400
        
        # Get manual dialer instance
        if campaign_id not in dialer_service.active_campaigns:
            return jsonify({'error': {'code': 'DIALER_NOT_RUNNING', 'message': 'Dialer is not running for this campaign'}}), 400
        
        manual_dialer = dialer_service.active_campaigns[campaign_id]
        if not hasattr(manual_dialer, 'manual_call'):
            return jsonify({'error': {'code': 'INVALID_DIALER_TYPE', 'message': 'Not a manual dialer'}}), 400
        
        # Initiate manual call
        call_id = manual_dialer.manual_call(lead_id, current_user_id)
        
        if call_id:
            return jsonify({
                'call_id': call_id,
                'lead_id': lead_id,
                'campaign_id': campaign_id,
                'agent_id': current_user_id,
                'status': 'initiated',
                'started_at': datetime.utcnow().isoformat()
            }), 201
        else:
            return jsonify({'error': {'code': 'CALL_INITIATION_FAILED', 'message': 'Failed to initiate manual call'}}), 500
            
    except Exception as e:
        return jsonify({'error': {'code': 'MANUAL_CALL_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/agent/status', methods=['PUT'])
@jwt_required()
def update_agent_status():
    """Update agent status (available, busy, offline)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('status'):
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'status is required'}}), 400
        
        status = data.get('status')
        valid_statuses = ['available', 'busy', 'offline']
        
        if status not in valid_statuses:
            return jsonify({'error': {'code': 'INVALID_STATUS', 'message': f'Status must be one of: {valid_statuses}'}}), 400
        
        # Update agent status
        dialer_service.update_agent_status(current_user_id, status)
        
        return jsonify({
            'agent_id': current_user_id,
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'UPDATE_AGENT_STATUS_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/agent/status', methods=['GET'])
@jwt_required()
def get_agent_status():
    """Get current agent status"""
    try:
        current_user_id = get_jwt_identity()
        
        agent_status = dialer_service.get_agent_status(current_user_id)
        
        if agent_status:
            return jsonify({
                'agent_id': current_user_id,
                'status': agent_status.status,
                'current_call_id': agent_status.current_call_id,
                'calls_today': agent_status.calls_today,
                'talk_time_today': agent_status.talk_time_today,
                'last_call_end': agent_status.last_call_end.isoformat() if agent_status.last_call_end else None
            }), 200
        else:
            return jsonify({
                'agent_id': current_user_id,
                'status': 'offline',
                'current_call_id': None,
                'calls_today': 0,
                'talk_time_today': 0,
                'last_call_end': None
            }), 200
            
    except Exception as e:
        return jsonify({'error': {'code': 'GET_AGENT_STATUS_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/leads/next', methods=['GET'])
@jwt_required()
def get_next_lead():
    """Get next lead for manual dialing"""
    try:
        current_user_id = get_jwt_identity()
        campaign_id = request.args.get('campaign_id', type=int)
        
        if not campaign_id:
            return jsonify({'error': {'code': 'MISSING_CAMPAIGN_ID', 'message': 'campaign_id parameter is required'}}), 400
        
        # Check if user is assigned to campaign (for agents)
        claims = get_jwt()
        user_role = claims.get('role')
        if user_role == 'agent':
            assignment = CampaignAssignment.query.filter_by(
                campaign_id=campaign_id,
                user_id=current_user_id
            ).first()
            if not assignment:
                return jsonify({'error': {'code': 'ACCESS_DENIED', 'message': 'Not assigned to this campaign'}}), 403
        
        # Get next lead
        lead = dialer_service.get_next_lead(campaign_id)
        
        if lead:
            return jsonify(lead.to_dict()), 200
        else:
            return jsonify({'message': 'No leads available'}), 404
            
    except Exception as e:
        return jsonify({'error': {'code': 'GET_NEXT_LEAD_ERROR', 'message': str(e)}}), 500

@dialer_bp.route('/dialer/campaigns/<int:campaign_id>/statistics', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_dialer_statistics(campaign_id):
    """Get detailed dialer statistics for a campaign"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Get statistics from dialer service
        stats = dialer_service.get_campaign_stats(campaign_id)
        
        # Get additional statistics from database
        from src.models import Call
        from sqlalchemy import func
        
        # Get calls from today
        today = datetime.utcnow().date()
        today_calls = Call.query.filter(
            Call.campaign_id == campaign_id,
            func.date(Call.started_at) == today
        ).all()
        
        # Calculate detailed statistics
        total_calls_today = len(today_calls)
        answered_calls_today = len([c for c in today_calls if c.call_status == 'answered'])
        busy_calls_today = len([c for c in today_calls if c.call_status == 'busy'])
        no_answer_calls_today = len([c for c in today_calls if c.call_status == 'no_answer'])
        failed_calls_today = len([c for c in today_calls if c.call_status == 'failed'])
        
        # Calculate talk time
        total_talk_time_today = sum([c.duration_seconds or 0 for c in today_calls if c.call_status == 'answered'])
        
        # Get agent performance
        agent_performance = {}
        assignments = CampaignAssignment.query.filter_by(campaign_id=campaign_id).all()
        
        for assignment in assignments:
            agent_calls = [c for c in today_calls if c.agent_id == assignment.user_id]
            agent_answered = [c for c in agent_calls if c.call_status == 'answered']
            agent_talk_time = sum([c.duration_seconds or 0 for c in agent_answered])
            
            agent_performance[assignment.user_id] = {
                'total_calls': len(agent_calls),
                'answered_calls': len(agent_answered),
                'answer_rate': len(agent_answered) / len(agent_calls) if agent_calls else 0,
                'talk_time': agent_talk_time,
                'average_call_duration': agent_talk_time / len(agent_answered) if agent_answered else 0
            }
        
        response = {
            'campaign_id': campaign_id,
            'dialer_mode': campaign.dialer_mode,
            'today_statistics': {
                'total_calls': total_calls_today,
                'answered_calls': answered_calls_today,
                'busy_calls': busy_calls_today,
                'no_answer_calls': no_answer_calls_today,
                'failed_calls': failed_calls_today,
                'answer_rate': answered_calls_today / total_calls_today if total_calls_today > 0 else 0,
                'total_talk_time': total_talk_time_today,
                'average_call_duration': total_talk_time_today / answered_calls_today if answered_calls_today > 0 else 0
            },
            'agent_performance': agent_performance
        }
        
        # Add real-time statistics if available
        if stats:
            response['realtime_statistics'] = {
                'total_calls': stats.total_calls,
                'answered_calls': stats.answered_calls,
                'busy_calls': stats.busy_calls,
                'no_answer_calls': stats.no_answer_calls,
                'failed_calls': stats.failed_calls,
                'answer_rate': stats.answer_rate,
                'average_call_duration': stats.average_call_duration,
                'agent_utilization': stats.agent_utilization
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_DIALER_STATISTICS_ERROR', 'message': str(e)}}), 500


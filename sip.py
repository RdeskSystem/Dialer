from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from src.models import db, SipConfiguration, SipChannel
from src.services.sip_service import sip_service

sip_bp = Blueprint('sip', __name__)

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

@sip_bp.route('/sip/configurations', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_sip_configurations():
    """Get all SIP configurations"""
    try:
        configurations = SipConfiguration.query.all()
        return jsonify({
            'configurations': [config.to_dict() for config in configurations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_SIP_CONFIGS_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def create_sip_configuration():
    """Create a new SIP configuration"""
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['name', 'host', 'username', 'password']):
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Name, host, username, and password are required'}}), 400
        
        # Check if name already exists
        existing_config = SipConfiguration.query.filter_by(name=data['name']).first()
        if existing_config:
            return jsonify({'error': {'code': 'CONFIG_EXISTS', 'message': 'Configuration name already exists'}}), 400
        
        # Create new configuration
        config = SipConfiguration(
            name=data['name'],
            host=data['host'],
            port=data.get('port', 5060),
            username=data['username']
        )
        
        # Set encrypted password
        config.set_password(data['password'])
        
        # Set codecs
        codecs = data.get('codecs', ['G711A', 'G729'])
        config.set_codecs(codecs)
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify(config.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'CREATE_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_sip_configuration(config_id):
    """Get a specific SIP configuration"""
    try:
        config = SipConfiguration.query.get_or_404(config_id)
        return jsonify(config.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>', methods=['PUT'])
@jwt_required()
@require_role(['admin'])
def update_sip_configuration(config_id):
    """Update a SIP configuration"""
    try:
        config = SipConfiguration.query.get_or_404(config_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Request data is required'}}), 400
        
        # Update basic fields
        if 'name' in data:
            # Check if name already exists (excluding current config)
            existing_config = SipConfiguration.query.filter(
                SipConfiguration.name == data['name'],
                SipConfiguration.id != config_id
            ).first()
            if existing_config:
                return jsonify({'error': {'code': 'CONFIG_EXISTS', 'message': 'Configuration name already exists'}}), 400
            config.name = data['name']
        
        if 'host' in data:
            config.host = data['host']
        if 'port' in data:
            config.port = data['port']
        if 'username' in data:
            config.username = data['username']
        
        # Update password if provided
        if 'password' in data:
            config.set_password(data['password'])
        
        # Update codecs
        if 'codecs' in data:
            config.set_codecs(data['codecs'])
        
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(config.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'UPDATE_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>', methods=['DELETE'])
@jwt_required()
@require_role(['admin'])
def delete_sip_configuration(config_id):
    """Delete a SIP configuration"""
    try:
        config = SipConfiguration.query.get_or_404(config_id)
        
        # Check if configuration is currently active
        if config.is_active:
            return jsonify({'error': {'code': 'CONFIG_IS_ACTIVE', 'message': 'Cannot delete active configuration'}}), 400
        
        db.session.delete(config)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'DELETE_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>/test', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def test_sip_configuration(config_id):
    """Test SIP configuration connectivity"""
    try:
        result = sip_service.test_sip_configuration(config_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        return jsonify({'error': {'code': 'TEST_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>/activate', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def activate_sip_configuration(config_id):
    """Activate a SIP configuration"""
    try:
        config = SipConfiguration.query.get_or_404(config_id)
        
        # Test configuration before activating
        test_result = sip_service.test_sip_configuration(config_id)
        if not test_result['success']:
            return jsonify({
                'success': False,
                'message': f'Configuration test failed: {test_result["message"]}'
            }), 400
        
        # Deactivate all other configurations
        SipConfiguration.query.update({'is_active': False})
        
        # Activate this configuration
        config.is_active = True
        db.session.commit()
        
        # Initialize AMI connection
        if sip_service.initialize_ami_connection(config_id):
            return jsonify({
                'success': True,
                'message': 'Configuration activated successfully'
            }), 200
        else:
            # Rollback activation if AMI connection fails
            config.is_active = False
            db.session.commit()
            return jsonify({
                'success': False,
                'message': 'Failed to initialize AMI connection'
            }), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'ACTIVATE_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/configurations/<int:config_id>/deactivate', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def deactivate_sip_configuration(config_id):
    """Deactivate a SIP configuration"""
    try:
        config = SipConfiguration.query.get_or_404(config_id)
        
        if not config.is_active:
            return jsonify({'error': {'code': 'CONFIG_NOT_ACTIVE', 'message': 'Configuration is not active'}}), 400
        
        # Check for active calls
        active_calls = sip_service.get_active_calls()
        if active_calls:
            return jsonify({
                'error': {
                    'code': 'ACTIVE_CALLS_EXIST',
                    'message': f'Cannot deactivate configuration with {len(active_calls)} active calls'
                }
            }), 400
        
        # Deactivate configuration
        config.is_active = False
        db.session.commit()
        
        # Shutdown AMI connection
        if config_id in sip_service.ami_clients:
            ami_client = sip_service.ami_clients[config_id]
            ami_client.stop_event_loop()
            ami_client.disconnect()
            del sip_service.ami_clients[config_id]
        
        return jsonify({
            'success': True,
            'message': 'Configuration deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'DEACTIVATE_SIP_CONFIG_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/status', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor', 'agent'])
def get_sip_status():
    """Get current SIP status and active calls"""
    try:
        active_config = sip_service.get_active_configuration()
        active_calls = sip_service.get_active_calls()
        
        status = {
            'active_configuration': active_config.to_dict() if active_config else None,
            'active_calls_count': len(active_calls),
            'active_calls': list(active_calls.keys()),
            'ami_connected': active_config.id in sip_service.ami_clients if active_config else False
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_SIP_STATUS_ERROR', 'message': str(e)}}), 500

@sip_bp.route('/sip/channels', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_sip_channels():
    """Get SIP channel status"""
    try:
        active_config = sip_service.get_active_configuration()
        if not active_config:
            return jsonify({'error': {'code': 'NO_ACTIVE_CONFIG', 'message': 'No active SIP configuration'}}), 400
        
        channels = SipChannel.query.filter_by(configuration_id=active_config.id).all()
        
        return jsonify({
            'channels': [channel.to_dict() for channel in channels]
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_SIP_CHANNELS_ERROR', 'message': str(e)}}), 500


from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from src.models.user import User, UserSession, db
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': {'code': 'MISSING_CREDENTIALS', 'message': 'Username and password are required'}}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': {'code': 'INVALID_CREDENTIALS', 'message': 'Invalid username or password'}}), 401
        
        if not user.is_active:
            return jsonify({'error': {'code': 'ACCOUNT_DISABLED', 'message': 'Account is disabled'}}), 401
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return jsonify({'error': {'code': 'ACCOUNT_LOCKED', 'message': 'Account is temporarily locked'}}), 401
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        
        # Create JWT tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'role': user.role, 'username': user.username}
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        # Create user session
        session_token = str(uuid.uuid4())
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=datetime.utcnow() + timedelta(days=7),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(user_session)
        db.session.commit()
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': 3600,
            'user': user.to_dict_safe()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'LOGIN_ERROR', 'message': str(e)}}), 500

@auth_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': {'code': 'INVALID_USER', 'message': 'User not found or inactive'}}), 401
        
        # Create new access token
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'role': user.role, 'username': user.username}
        )
        
        return jsonify({
            'access_token': access_token,
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'REFRESH_ERROR', 'message': str(e)}}), 500

@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user and invalidate session"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get session token from request headers if available
        session_token = request.headers.get('X-Session-Token')
        
        if session_token:
            # Find and delete the specific session
            user_session = UserSession.query.filter_by(
                user_id=current_user_id,
                session_token=session_token
            ).first()
            
            if user_session:
                db.session.delete(user_session)
                db.session.commit()
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'LOGOUT_ERROR', 'message': str(e)}}), 500

@auth_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': {'code': 'USER_NOT_FOUND', 'message': 'User not found'}}), 404
        
        return jsonify({'user': user.to_dict_safe()}), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_USER_ERROR', 'message': str(e)}}), 500

@auth_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': {'code': 'USER_NOT_FOUND', 'message': 'User not found'}}), 404
        
        data = request.get_json()
        
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Current password and new password are required'}}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': {'code': 'INVALID_PASSWORD', 'message': 'Current password is incorrect'}}), 400
        
        # Validate new password strength
        if len(new_password) < 8:
            return jsonify({'error': {'code': 'WEAK_PASSWORD', 'message': 'Password must be at least 8 characters long'}}), 400
        
        # Set new password
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'CHANGE_PASSWORD_ERROR', 'message': str(e)}}), 500



@auth_bp.route('/auth/register-admin', methods=['POST'])
def register_admin():
    """Temporary endpoint to register an admin user - NO AUTHENTICATION REQUIRED"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Request data is required'}}), 400
        
        # Required fields
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        first_name = data.get('first_name', 'Admin')
        last_name = data.get('last_name', 'User')
        
        if not username or not password or not email:
            return jsonify({'error': {'code': 'MISSING_FIELDS', 'message': 'Username, password, and email are required'}}), 400
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return jsonify({'error': {'code': 'USER_EXISTS', 'message': 'User with this username or email already exists'}}), 409
        
        # Create new admin user
        new_user = User(
            username=username,
            email=email,
            role='admin',
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create access token for immediate login
        access_token = create_access_token(
            identity=new_user.id,
            additional_claims={'role': new_user.role, 'username': new_user.username}
        )
        refresh_token = create_refresh_token(identity=new_user.id)
        
        # Update last login
        new_user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Admin user created successfully',
            'user': new_user.to_dict_safe(),
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'REGISTRATION_FAILED', 'message': f'Failed to create admin user: {str(e)}'}}), 500

@auth_bp.route('/auth/setup-status', methods=['GET'])
def setup_status():
    """Check if system has any admin users - NO AUTHENTICATION REQUIRED"""
    try:
        admin_count = User.query.filter_by(role='admin', is_active=True).count()
        
        return jsonify({
            'has_admin': admin_count > 0,
            'admin_count': admin_count,
            'setup_required': admin_count == 0,
            'registration_endpoint': '/api/auth/register-admin'
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'STATUS_CHECK_FAILED', 'message': f'Failed to check setup status: {str(e)}'}}), 500


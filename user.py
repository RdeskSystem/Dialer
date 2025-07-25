from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from src.models import User, db

user_bp = Blueprint('user', __name__)

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

@user_bp.route('/users', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_users():
    """Get users with filtering and pagination"""
    try:
        # Query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        role = request.args.get('role')
        active = request.args.get('active', type=bool)
        
        # Base query
        query = User.query
        
        # Apply filters
        if role:
            query = query.filter(User.role == role)
        if active is not None:
            query = query.filter(User.is_active == active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        users = query.offset((page - 1) * limit).limit(limit).all()
        
        # Calculate pages
        pages = (total + limit - 1) // limit
        
        return jsonify({
            'users': [user.to_dict() for user in users],
            'total': total,
            'page': page,
            'pages': pages
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_USERS_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def create_user():
    """Create a new user"""
    try:
        data = request.json
        
        if not data or not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Username, email, and password are required'}}), 400
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == data.get('username')) | (User.email == data.get('email'))
        ).first()
        
        if existing_user:
            return jsonify({'error': {'code': 'USER_EXISTS', 'message': 'Username or email already exists'}}), 400
        
        # Validate role
        valid_roles = ['admin', 'supervisor', 'agent']
        role = data.get('role', 'agent')
        if role not in valid_roles:
            return jsonify({'error': {'code': 'INVALID_ROLE', 'message': 'Invalid role specified'}}), 400
        
        # Create user
        user = User(
            username=data.get('username'),
            email=data.get('email'),
            role=role,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            is_active=data.get('is_active', True)
        )
        
        # Set password
        user.set_password(data.get('password'))
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'CREATE_USER_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get a specific user"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_role = claims.get('role')
        
        # Users can view their own profile, admins and supervisors can view any user
        if user_id != current_user_id and user_role not in ['admin', 'supervisor']:
            return jsonify({'error': {'code': 'ACCESS_DENIED', 'message': 'Access denied'}}), 403
        
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_USER_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update a user"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_role = claims.get('role')
        
        user = User.query.get_or_404(user_id)
        data = request.json
        
        if not data:
            return jsonify({'error': {'code': 'MISSING_DATA', 'message': 'Request data is required'}}), 400
        
        # Check permissions
        is_self_update = user_id == current_user_id
        is_admin_or_supervisor = user_role in ['admin', 'supervisor']
        
        if not is_self_update and not is_admin_or_supervisor:
            return jsonify({'error': {'code': 'ACCESS_DENIED', 'message': 'Access denied'}}), 403
        
        # Update basic fields (allowed for self and admin/supervisor)
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            # Check if email is already taken by another user
            existing_user = User.query.filter(
                User.email == data['email'],
                User.id != user_id
            ).first()
            if existing_user:
                return jsonify({'error': {'code': 'EMAIL_EXISTS', 'message': 'Email already exists'}}), 400
            user.email = data['email']
        
        # Admin/supervisor only fields
        if is_admin_or_supervisor:
            if 'username' in data:
                # Check if username is already taken by another user
                existing_user = User.query.filter(
                    User.username == data['username'],
                    User.id != user_id
                ).first()
                if existing_user:
                    return jsonify({'error': {'code': 'USERNAME_EXISTS', 'message': 'Username already exists'}}), 400
                user.username = data['username']
            
            if 'role' in data:
                valid_roles = ['admin', 'supervisor', 'agent']
                if data['role'] in valid_roles:
                    user.role = data['role']
            
            if 'is_active' in data:
                user.is_active = data['is_active']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'UPDATE_USER_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_role(['admin'])
def delete_user(user_id):
    """Delete a user"""
    try:
        current_user_id = get_jwt_identity()
        
        # Prevent self-deletion
        if user_id == current_user_id:
            return jsonify({'error': {'code': 'CANNOT_DELETE_SELF', 'message': 'Cannot delete your own account'}}), 400
        
        user = User.query.get_or_404(user_id)
        
        # Check if user has active calls or assignments
        if user.calls or user.assigned_campaigns:
            return jsonify({'error': {'code': 'USER_HAS_DEPENDENCIES', 'message': 'Cannot delete user with active calls or campaign assignments'}}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'DELETE_USER_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@jwt_required()
@require_role(['admin'])
def reset_user_password(user_id):
    """Reset user password"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        if not data or not data.get('new_password'):
            return jsonify({'error': {'code': 'MISSING_PASSWORD', 'message': 'New password is required'}}), 400
        
        new_password = data.get('new_password')
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({'error': {'code': 'WEAK_PASSWORD', 'message': 'Password must be at least 8 characters long'}}), 400
        
        # Set new password
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        
        db.session.commit()
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': {'code': 'RESET_PASSWORD_ERROR', 'message': str(e)}}), 500

@user_bp.route('/users/agents', methods=['GET'])
@jwt_required()
@require_role(['admin', 'supervisor'])
def get_agents():
    """Get all agents for assignment purposes"""
    try:
        agents = User.query.filter(
            User.role.in_(['agent', 'supervisor']),
            User.is_active == True
        ).all()
        
        return jsonify({
            'agents': [agent.to_dict_safe() for agent in agents]
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'GET_AGENTS_ERROR', 'message': str(e)}}), 500


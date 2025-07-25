import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import timedelta, datetime

# Import all models to ensure they are registered
from src.models import (
    db, User, UserSession, Campaign, CampaignAssignment, CampaignStatistics,
    Lead, LeadHistory, Call, CallEvent, AgentPerformance, SipConfiguration, SipChannel
)

# Import all routes
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.campaign import campaign_bp
from src.routes.sip import sip_bp
from src.routes.call import call_bp
from src.routes.dialer import dialer_bp
from src.routes.lead import lead_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'telephony-crm-production-secret-key-2025')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-telephony-crm-production-key-2025')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
cors = CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(campaign_bp, url_prefix='/api')
app.register_blueprint(sip_bp, url_prefix='/api')
app.register_blueprint(call_bp, url_prefix='/api')
app.register_blueprint(dialer_bp, url_prefix='/api')
app.register_blueprint(lead_bp, url_prefix='/api')

# JWT error handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired'}}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid token'}}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': {'code': 'MISSING_TOKEN', 'message': 'Authorization token is required'}}), 401

@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return jsonify({'error': {'code': 'FRESH_TOKEN_REQUIRED', 'message': 'Fresh token required'}}), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': {'code': 'TOKEN_REVOKED', 'message': 'Token has been revoked'}}), 401

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@telephonycrm.com',
            role='admin',
            first_name='System',
            last_name='Administrator'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("Created default admin user: admin / admin123")

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200

# WebSocket events for real-time features
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_dashboard')
def handle_join_dashboard(data):
    """Join dashboard room for real-time updates"""
    # In a production environment, you would verify JWT token here
    print(f'Client joined dashboard: {data}')

# Static file serving for frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)


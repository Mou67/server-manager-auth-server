import os
import json
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import jwt
import requests

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS

# CRITICAL: Set before flask_discord import
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

from flask_discord import DiscordOAuth2Session

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Discord OAuth2
app.config['DISCORD_CLIENT_ID'] = os.getenv('DISCORD_CLIENT_ID', '1234567890')
app.config['DISCORD_CLIENT_SECRET'] = os.getenv('DISCORD_CLIENT_SECRET', 'your_secret')
app.config['DISCORD_BOT_TOKEN'] = os.getenv('DISCORD_BOT_TOKEN', 'your_bot_token')
app.config['DISCORD_REDIRECT_URI'] = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5001/auth/discord/callback')

discord = DiscordOAuth2Session(app)

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 86400 * 7  # 7 days

# Logging Directories
LOG_DIR = 'logs'
DATA_DIR = 'data'

for directory in [LOG_DIR, DATA_DIR]:
    os.makedirs(directory, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')
AUTH_LOG_FILE = os.path.join(LOG_DIR, 'auth.log')
ACTIONS_LOG_FILE = os.path.join(LOG_DIR, 'actions.log')
ERRORS_LOG_FILE = os.path.join(LOG_DIR, 'errors.log')

# ===== LOGGING FUNCTIONS =====

def log_auth(event_type, user_id=None, username=None, details=None):
    """Log authentication events"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'username': username,
        'details': details or {}
    }
    
    try:
        with open(AUTH_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"❌ Error logging auth event: {e}")


def log_action(action_type, user_id, username, action_details, ip_address=None):
    """Log all user actions"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action_type': action_type,
        'user_id': user_id,
        'username': username,
        'action_details': action_details,
        'ip_address': ip_address or request.remote_addr
    }
    
    try:
        with open(ACTIONS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"❌ Error logging action: {e}")


def log_error(error_type, error_message, user_id=None, details=None):
    """Log errors"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'error_type': error_type,
        'error_message': str(error_message),
        'user_id': user_id,
        'details': details or {},
        'ip_address': request.remote_addr if request else 'N/A'
    }
    
    try:
        with open(ERRORS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"❌ Error logging error: {e}")


# ===== USER MANAGEMENT =====

def load_users():
    """Load all users from JSON"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log_error('LOAD_USERS', e)
    return {}


def save_user(user_id, user_data):
    """Save user data to JSON"""
    try:
        users = load_users()
        users[str(user_id)] = user_data
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log_error('SAVE_USER', e, user_id)
        return False


def generate_jwt_token(user_id, username):
    """Generate JWT token for user"""
    try:
        payload = {
            'user_id': str(user_id),
            'username': username,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    except Exception as e:
        log_error('JWT_GENERATION', e, user_id)
        return None


def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        log_error('JWT_EXPIRED', 'Token expired', details={'token': token[:10]})
        return None
    except jwt.InvalidTokenError as e:
        log_error('JWT_INVALID', e, details={'token': token[:10]})
        return None


# ===== AUTHENTICATION ROUTES =====

@app.route('/auth/discord/login')
def discord_login():
    """Initiate Discord OAuth"""
    log_action('OAUTH_LOGIN_INITIATED', None, 'anonymous', {'source': 'discord'})
    return discord.create_session(scopes=['identify', 'email'], prompt=False)


@app.route('/auth/discord/callback')
def discord_callback():
    """Handle Discord OAuth callback"""
    try:
        # Handle CSRF state mismatch
        try:
            discord.callback()
        except Exception as callback_error:
            print(f"⚠️ Discord Callback Error (ignoriert): {callback_error}")
            log_auth('CSRF_WARNING', details={'error': str(callback_error)})
        
        user = discord.fetch_user()
        user_id = user.id
        username = user.name
        
        # Prepare user data
        user_data = {
            'discord_id': user_id,
            'username': username,
            'email': getattr(user, 'email', None),
            'avatar': getattr(user, 'avatar', None),
            'discriminator': getattr(user, 'discriminator', '0'),
            'first_login': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'login_count': 1
        }
        
        # Check if user exists
        existing_users = load_users()
        if str(user_id) in existing_users:
            # Update existing user
            existing_users[str(user_id)]['last_login'] = datetime.now().isoformat()
            existing_users[str(user_id)]['login_count'] = existing_users[str(user_id)].get('login_count', 0) + 1
            user_data = existing_users[str(user_id)]
        
        # Save user
        save_user(user_id, user_data)
        
        # Generate JWT token
        token = generate_jwt_token(user_id, username)
        
        if not token:
            log_error('TOKEN_GENERATION_FAILED', 'Could not generate JWT', user_id)
            return redirect(f"{request.args.get('redirect_uri', 'http://localhost:5000')}?error=token_failed")
        
        # Log successful authentication
        log_auth('LOGIN_SUCCESS', user_id, username, {'method': 'discord'})
        log_action('USER_LOGIN', user_id, username, {'method': 'discord'})
        
        print(f"✅ Discord User angemeldet: {username} (ID: {user_id})")
        
        # Redirect back to local app with token
        redirect_uri = request.args.get('redirect_uri', 'http://localhost:5000')
        return redirect(f"{redirect_uri}?token={token}&user_id={user_id}&username={username}")
        
    except Exception as e:
        print(f"❌ Discord Callback Fehler: {e}")
        log_error('DISCORD_CALLBACK_ERROR', e)
        return redirect(f"{request.args.get('redirect_uri', 'http://localhost:5000')}?error={str(e)}")


@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        token = request.json.get('token')
        payload = verify_jwt_token(token)
        
        if payload:
            user_id = payload.get('user_id')
            username = payload.get('username')
            
            log_auth('LOGOUT', user_id, username)
            log_action('USER_LOGOUT', user_id, username, {})
            
            print(f"✅ User logged out: {username} (ID: {user_id})")
            
            return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
    except Exception as e:
        log_error('LOGOUT_ERROR', e)
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== API ENDPOINTS =====

@app.route('/api/validate-token', methods=['POST'])
def validate_token():
    """Validate JWT token from local app"""
    try:
        token = request.json.get('token')
        
        if not token:
            return jsonify({'valid': False, 'message': 'Token required'}), 400
        
        payload = verify_jwt_token(token)
        
        if payload:
            user_id = payload.get('user_id')
            log_action('TOKEN_VALIDATION_SUCCESS', user_id, payload.get('username'), {'action': 'validate_token'})
            
            return jsonify({
                'valid': True,
                'user_id': user_id,
                'username': payload.get('username'),
                'exp': payload.get('exp')
            }), 200
        else:
            return jsonify({'valid': False, 'message': 'Invalid or expired token'}), 401
            
    except Exception as e:
        log_error('TOKEN_VALIDATION_ERROR', e)
        return jsonify({'valid': False, 'message': str(e)}), 500


@app.route('/api/log-action', methods=['POST'])
def log_action_api():
    """Log action from local app"""
    try:
        data = request.json
        token = data.get('token')
        action_type = data.get('action_type')
        action_details = data.get('action_details', {})
        
        # Validate token
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        username = payload.get('username')
        
        # Log the action
        log_action(action_type, user_id, username, action_details)
        
        print(f"📝 Action logged: {action_type} by {username}")
        
        return jsonify({'success': True, 'message': 'Action logged'}), 200
        
    except Exception as e:
        log_error('LOG_ACTION_ERROR', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (admin endpoint)"""
    try:
        admin_token = request.args.get('admin_token')
        
        # Simple admin check (in production use proper admin verification)
        if admin_token != os.getenv('ADMIN_TOKEN', 'admin123'):
            return jsonify({'error': 'Unauthorized'}), 401
        
        users = load_users()
        
        return jsonify({
            'total_users': len(users),
            'users': users
        }), 200
        
    except Exception as e:
        log_error('GET_USERS_ERROR', e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get logs (admin endpoint)"""
    try:
        admin_token = request.args.get('admin_token')
        log_type = request.args.get('type', 'auth')  # auth, actions, errors
        limit = int(request.args.get('limit', 100))
        
        # Simple admin check
        if admin_token != os.getenv('ADMIN_TOKEN', 'admin123'):
            return jsonify({'error': 'Unauthorized'}), 401
        
        if log_type == 'auth':
            log_file = AUTH_LOG_FILE
        elif log_type == 'actions':
            log_file = ACTIONS_LOG_FILE
        elif log_type == 'errors':
            log_file = ERRORS_LOG_FILE
        else:
            return jsonify({'error': 'Invalid log type'}), 400
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
        except FileNotFoundError:
            pass
        
        return jsonify({
            'log_type': log_type,
            'total_logs': len(logs),
            'logs': logs
        }), 200
        
    except Exception as e:
        log_error('GET_LOGS_ERROR', e)
        return jsonify({'error': str(e)}), 500


# ===== HEALTH CHECK =====

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'name': 'Server Manager OAuth Server',
        'version': '1.0.0',
        'endpoints': {
            'auth': ['/auth/discord/login', '/auth/discord/callback', '/auth/logout'],
            'api': ['/api/validate-token', '/api/log-action', '/api/users', '/api/logs'],
            'health': '/health'
        }
    }), 200


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    log_error('NOT_FOUND', error)
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    log_error('INTERNAL_ERROR', error)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    
    print(f"""
    ╔════════════════════════════════════════════════╗
    ║   Server Manager OAuth Server                  ║
    ║   Port: {port}                                   ║
    ║   Debug: {debug}                                 ║
    ╚════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)

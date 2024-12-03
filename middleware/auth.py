from functools import wraps
from flask import request, jsonify
import jwt
from config.database import Database
from bson import ObjectId

db = Database.get_instance().db
SECRET_KEY = "your_jwt_secret_key"  # Move to environment variables in production

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = db.users.find_one({"_id": ObjectId(payload["user_id"])})
        return user
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def auth_middleware():
    # Skip auth for certain routes
    public_routes = [
        '/',
        '/health', 
        '/api/test', 
        '/api/auth/login', 
        '/api/ports', 
        '/api/ports/search',
        '/api/shipping-lines',
        '/api/shipping-lines/search',
        '/api/rates/search'
    ]
    
    if request.path in public_routes or request.method == 'OPTIONS':
        return None

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "No authorization header"}), 401

    try:
        token = auth_header.split(" ")[1]
        user = verify_token(token)
        
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
            
        request.current_user = user
        
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
            
        try:
            token = auth_header.split(" ")[1]
            user = verify_token(token)
            
            if not user:
                return jsonify({"error": "Invalid or expired token"}), 401
                
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 401
            
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
            
        try:
            token = auth_header.split(" ")[1]
            user = verify_token(token)
            
            if not user:
                return jsonify({"error": "Invalid or expired token"}), 401
                
            if user.get('role') != 'admin':
                return jsonify({"error": "Admin access required"}), 403
                
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 401
            
    return decorated 
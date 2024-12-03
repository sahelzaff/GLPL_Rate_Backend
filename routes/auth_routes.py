from flask import Blueprint, request, jsonify
from config.database import Database
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from services.activity_logger import activity_logger

auth_routes = Blueprint('auth_routes', __name__)
db = Database.get_instance().db

SECRET_KEY = "your_jwt_secret_key"  # Move to environment variables in production

@auth_routes.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Find user by email
        user = db.users.find_one({"email": email.lower()})
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate JWT token
        token = jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(days=1)
        }, SECRET_KEY, algorithm='HS256')
        
        # Log login activity
        activity_logger.log_activity(
            'user_login',
            {
                'user_email': user['email'],
                'role': user['role']
            },
            user
        )

        return jsonify({
            "token": token,
            "user": {
                "id": str(user['_id']),
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "company": user.get('company', '')
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_routes.route('/api/auth/logout', methods=['POST'])
def logout():
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(" ")[1]
            try:
                # Decode token to get user info
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user = db.users.find_one({"_id": ObjectId(payload["user_id"])})
                
                if user:
                    # Log logout activity
                    activity_logger.log_activity(
                        'user_logout',
                        {
                            'user_email': user['email'],
                            'role': user['role']
                        },
                        user
                    )
            except:
                pass  # Token might be expired, but we still want to return success
                
        return jsonify({"message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_routes.route('/api/auth/verify', methods=['GET'])
def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "No token provided"}), 401

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = db.users.find_one({"_id": ObjectId(payload["user_id"])})
        
        if not user:
            return jsonify({"error": "User not found"}), 401

        return jsonify({
            "valid": True,
            "user": {
                "id": str(user['_id']),
                "email": user['email'],
                "name": user['name'],
                "role": user['role']
            }
        })
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401 
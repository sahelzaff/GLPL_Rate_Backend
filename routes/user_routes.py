from flask import Blueprint, request, jsonify
from bson import ObjectId
import bcrypt
from middleware.auth import admin_required
from config.database import Database
from datetime import datetime
from services.activity_logger import activity_logger

user_routes = Blueprint('user_routes', __name__)
db = Database.get_instance().db

@user_routes.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    try:
        users = list(db.users.find({}, {'password': 0}))  # Exclude password
        return jsonify([{
            **{k: str(v) if k == '_id' else v for k, v in user.items()}
        } for user in users])
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_routes.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    try:
        data = request.json
        required_fields = ['name', 'email', 'password', 'role']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Check if user already exists
        if db.users.find_one({"email": data['email'].lower()}):
            return jsonify({"error": "User with this email already exists"}), 409
            
        # Hash password
        hashed_password = bcrypt.hashpw(
            data['password'].encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Prepare user data
        user_data = {
            'name': data['name'],
            'email': data['email'].lower(),
            'password': hashed_password,
            'role': data['role'],
            'company': data.get('company', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.users.insert_one(user_data)
        
        # Log activity
        try:
            activity_logger.log_activity(
                'user_created',
                {
                    'user_id': str(result.inserted_id),
                    'user_details': {
                        'name': user_data['name'],
                        'email': user_data['email'],
                        'role': user_data['role'],
                        'company': user_data.get('company', '')
                    }
                },
                request.current_user
            )
        except Exception as e:
            print(f"Warning: Failed to log activity: {str(e)}")
        
        return jsonify({
            "message": "User created successfully",
            "id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_routes.route('/api/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.json
        update_data = {}

        # Handle basic fields
        for field in ['name', 'email', 'role', 'company']:
            if field in data:
                update_data[field] = data[field]

        # Handle password separately
        if 'password' in data and data['password']:
            update_data['password'] = bcrypt.hashpw(
                data['password'].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

        # Add updated timestamp
        update_data['updated_at'] = datetime.utcnow()

        # Get original user data for activity log
        original_user = db.users.find_one({"_id": ObjectId(user_id)})
        if not original_user:
            return jsonify({"error": "User not found"}), 404

        # Perform update
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        if result.modified_count:
            # Log activity
            try:
                activity_logger.log_activity(
                    'user_updated',
                    {
                        'user_id': str(user_id),
                        'changes': {k: v for k, v in update_data.items() if k != 'password'},
                        'original': {k: str(v) if k == '_id' else v for k, v in original_user.items() if k != 'password'}
                    },
                    request.current_user
                )
            except Exception as e:
                print(f"Warning: Failed to log activity: {str(e)}")
                
            return jsonify({"message": "User updated successfully"})
        return jsonify({"error": "No changes made"}), 200

    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_routes.route('/api/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        # Get user data before deletion for activity log
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404

        result = db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count:
            # Log activity
            try:
                activity_logger.log_activity(
                    'user_deleted',
                    {
                        'user_id': str(user_id),
                        'user_details': {
                            'name': user['name'],
                            'email': user['email'],
                            'role': user['role'],
                            'company': user.get('company', '')
                        }
                    },
                    request.current_user
                )
            except Exception as e:
                print(f"Warning: Failed to log activity: {str(e)}")
                
            return jsonify({"message": "User deleted successfully"})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({"error": str(e)}), 500 
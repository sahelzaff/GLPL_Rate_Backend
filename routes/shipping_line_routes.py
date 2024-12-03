from flask import Blueprint, request, jsonify
from bson import ObjectId
from middleware.auth import require_auth, admin_required
from config.database import Database
from datetime import datetime

shipping_line_routes = Blueprint('shipping_line_routes', __name__)
db = Database.get_instance().db

@shipping_line_routes.route('/api/shipping-lines', methods=['GET'])
def get_shipping_lines():
    try:
        shipping_lines = list(db.shipping_lines.find())
        return jsonify([{
            '_id': str(line['_id']),
            'name': line['name'],
            'contact_email': line['contact_email'],
            'website': line.get('website', ''),
            'created_at': line.get('created_at', ''),
            'updated_at': line.get('updated_at', '')
        } for line in shipping_lines])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shipping_line_routes.route('/api/shipping-lines/search', methods=['GET'])
def search_shipping_lines():
    try:
        term = request.args.get('term', '')
        if len(term) < 2:
            return jsonify([])
            
        results = db.shipping_lines.find({
            "$or": [
                {"name": {"$regex": term, "$options": "i"}},
                {"contact_email": {"$regex": term, "$options": "i"}}
            ]
        })
        
        shipping_lines = [{
            'value': str(line['_id']),
            'label': f"{line['name']} ({line['contact_email']})"
        } for line in results]
        return jsonify(shipping_lines)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shipping_line_routes.route('/api/shipping-lines', methods=['POST'])
@admin_required
def add_shipping_line():
    try:
        data = request.json
        
        # Validate required fields
        if not all(data.get(field) for field in ['name', 'contact_email']):
            return jsonify({"error": "Name and contact email are required"}), 400
            
        # Check if shipping line already exists
        if db.shipping_lines.find_one({"name": data['name']}):
            return jsonify({"error": "Shipping line with this name already exists"}), 409
            
        result = db.shipping_lines.insert_one({
            'name': data['name'].strip(),
            'contact_email': data['contact_email'].strip().lower(),
            'website': data.get('website', '').strip(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return jsonify({
            "message": "Shipping line added successfully",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shipping_line_routes.route('/api/shipping-lines/<line_id>', methods=['PUT'])
@admin_required
def update_shipping_line(line_id):
    try:
        data = request.json
        result = db.shipping_lines.update_one(
            {"_id": ObjectId(line_id)},
            {
                "$set": {
                    **{k: v.strip() for k, v in data.items()},
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count:
            return jsonify({"message": "Shipping line updated successfully"})
        return jsonify({"error": "Shipping line not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shipping_line_routes.route('/api/shipping-lines/<line_id>', methods=['DELETE'])
@admin_required
def delete_shipping_line(line_id):
    try:
        result = db.shipping_lines.delete_one({"_id": ObjectId(line_id)})
        if result.deleted_count:
            return jsonify({"message": "Shipping line deleted successfully"})
        return jsonify({"error": "Shipping line not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... rest of your routes
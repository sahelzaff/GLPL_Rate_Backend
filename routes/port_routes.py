from flask import Blueprint, request, jsonify
from bson import ObjectId
from middleware.auth import require_auth, admin_required
from models.port import Port
from config.database import Database

port_routes = Blueprint('port_routes', __name__)
db = Database.get_instance().db
port_model = Port(db)

# Get all ports (no auth required)
@port_routes.route('/api/ports', methods=['GET'])
def get_ports():
    try:
        ports = list(port_model.get_all())
        return jsonify([{
            '_id': str(port['_id']),
            'port_code': port['port_code'],
            'port_name': port['port_name'],
            'country': port['country']
        } for port in ports])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Search ports (no auth required)
@port_routes.route('/api/ports/search', methods=['GET'])
def search_ports():
    try:
        term = request.args.get('term', '')
        if len(term) < 2:
            return jsonify([])
            
        results = port_model.search(term)
        ports = [{
            'code': port['port_code'],
            'label': f"{port['port_name']} ({port['port_code']}) - {port['country']}"
        } for port in results]
        return jsonify(ports)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add new port (admin only)
@port_routes.route('/api/ports', methods=['POST'])
@admin_required
def add_port():
    try:
        data = request.json
        required_fields = ['port_code', 'port_name', 'country']
        
        # Validate required fields
        if not all(data.get(field) for field in required_fields):
            return jsonify({"error": "Missing or empty required fields"}), 400
            
        # Check if port code already exists
        if port_model.find_by_code(data['port_code']):
            return jsonify({"error": "Port code already exists"}), 409
            
        # Clean the data
        port_data = {
            'port_code': data['port_code'].strip().upper(),
            'port_name': data['port_name'].strip(),
            'country': data['country'].strip(),
            'region': data.get('region', '').strip()  # Default to empty string
        }
        
        result = port_model.create(port_data)
        return jsonify({
            "message": "Port added successfully",
            "id": str(result.inserted_id)
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Update port (admin only)
@port_routes.route('/api/ports/<port_id>', methods=['PUT'])
@admin_required
def update_port(port_id):
    try:
        data = request.json
        result = port_model.update(port_id, data)
        if result.modified_count:
            return jsonify({"message": "Port updated successfully"})
        return jsonify({"error": "Port not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete port (admin only)
@port_routes.route('/api/ports/<port_id>', methods=['DELETE'])
@admin_required
def delete_port(port_id):
    try:
        result = port_model.delete(port_id)
        if result.deleted_count:
            return jsonify({"message": "Port deleted successfully"})
        return jsonify({"error": "Port not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
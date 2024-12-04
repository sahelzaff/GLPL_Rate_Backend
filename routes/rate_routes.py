from flask import Blueprint, request, jsonify, make_response
from bson import ObjectId
from datetime import datetime
from middleware.auth import require_auth
from models.rate import Rate
from config.database import Database

rate_routes = Blueprint('rate_routes', __name__)
db = Database.get_instance().db
rate_model = Rate(db)

@rate_routes.route('/api/rates', methods=['GET'])
@require_auth
def get_rates():
    # Add CORS headers
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        # Get all rates
        rates = list(rate_model.get_all())
        populated_rates = []
        
        for rate in rates:
            try:
                # Get related data with proper error handling
                shipping_line = None
                pol = None
                pod = None
                
                try:
                    if 'shipping_line_id' in rate:
                        shipping_line = db.shipping_lines.find_one({"_id": ObjectId(rate['shipping_line_id'])})
                except Exception:
                    pass

                try:
                    if 'pol_id' in rate:
                        pol = db.ports.find_one({"_id": ObjectId(rate['pol_id'])})
                except Exception:
                    pass

                try:
                    if 'pod_id' in rate:
                        pod = db.ports.find_one({"_id": ObjectId(rate['pod_id'])})
                except Exception:
                    pass
                
                # Format the rate data
                populated_rate = {
                    '_id': str(rate['_id']),
                    'shipping_line': shipping_line['name'] if shipping_line else 'Unknown',
                    'shipping_line_id': str(rate['shipping_line_id']) if 'shipping_line_id' in rate else None,
                    'pol': f"{pol['port_name']} ({pol['port_code']})" if pol else 'Unknown',
                    'pol_id': str(rate['pol_id']) if 'pol_id' in rate else None,
                    'pod': f"{pod['port_name']} ({pod['port_code']})" if pod else 'Unknown',
                    'pod_id': str(rate['pod_id']) if 'pod_id' in rate else None,
                    'valid_from': rate.get('valid_from'),
                    'valid_to': rate.get('valid_to'),
                    'container_rates': rate.get('container_rates', []),
                    'created_at': rate.get('created_at'),
                    'updated_at': rate.get('updated_at')
                }
                populated_rates.append(populated_rate)
            except Exception as e:
                print(f"Error populating rate {rate.get('_id')}: {str(e)}")
                continue

        return jsonify({
            'status': 'success',
            'data': populated_rates,
            'count': len(populated_rates)
        })

    except Exception as e:
        print(f"Error in get_rates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates/search', methods=['POST'])
def search_rates():
    try:
        data = request.json
        pol_code = data.get('pol_code')
        pod_code = data.get('pod_code')

        if not pol_code or not pod_code:
            return jsonify({"error": "POL and POD are required"}), 400

        # Find ports by their codes
        pol = db.ports.find_one({"port_code": pol_code.upper()})
        pod = db.ports.find_one({"port_code": pod_code.upper()})

        if not pol or not pod:
            return jsonify({"error": "Invalid port codes"}), 400

        # Get rates using port IDs
        rates = list(db.rates.find({
            "pol_id": pol['_id'],
            "pod_id": pod['_id']
        }))
        
        # Populate with shipping line details and include new fields
        populated_rates = []
        for rate in rates:
            shipping_line = db.shipping_lines.find_one({"_id": rate['shipping_line_id']})
            
            # Get notes for this rate
            notes = list(db.rate_notes.find({"rate_id": rate['_id']}))
            
            populated_rate = {
                'shippingLine': shipping_line['name'] if shipping_line else 'Unknown',
                'pol': f"{pol['port_name']} ({pol['port_code']})",
                'pod': f"{pod['port_name']} ({pod['port_code']})",
                'containerRates': [{
                    'type': cr['type'],
                    'base_rate': float(cr.get('base_rate', 0)),
                    'ewrs_laden': float(cr.get('ewrs_laden', 0)),
                    'ewrs_empty': float(cr.get('ewrs_empty', 0)),
                    'baf': float(cr.get('baf', 0)),
                    'reefer_surcharge': float(cr.get('reefer_surcharge', 0)),
                    'total_cost': float(cr.get('total_cost', 0)) or float(cr.get('base_rate', 0)) or float(cr.get('rate', 0)) or 0,
                    'rate': float(cr.get('rate', 0))  # Include legacy rate if it exists
                } for cr in rate['container_rates']],
                'validFrom': rate['valid_from'],
                'validTo': rate['valid_to'],
                'transitTime': rate.get('transit_time', 'N/A'),
                'remarks': rate.get('remarks', ''),
                'notes': [{
                    'id': str(note['_id']),
                    'description': note['description']
                } for note in notes]
            }
            populated_rates.append(populated_rate)

        return jsonify(populated_rates)

    except Exception as e:
        print(f"Error searching rates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates', methods=['POST'])
@require_auth
def create_rate():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['shipping_line', 'pol', 'pod', 'valid_from', 'valid_to', 'container_rates']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Create rate
        result = rate_model.create(data)
        
        return jsonify({
            "message": "Rate created successfully",
            "id": str(result.inserted_id)
        }), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error creating rate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/<rate_id>/history', methods=['GET'])
@require_auth
def get_rate_history(rate_id):
    try:
        history = rate_model.get_rate_history(rate_id)
        history_list = []
        
        for record in history:
            record['_id'] = str(record['_id'])
            record['rate_id'] = str(record['rate_id'])
            history_list.append(record)

        return jsonify(history_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/<rate_id>', methods=['DELETE'])
@require_auth
def delete_rate(rate_id):
    try:
        result = rate_model.delete(rate_id)
        if result.deleted_count:
            return jsonify({"message": "Rate deleted successfully"})
        return jsonify({"error": "Rate not found"}), 404
    except Exception as e:
        print(f"Error deleting rate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/<rate_id>', methods=['PUT'])
@require_auth
def update_rate(rate_id):
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['shipping_line', 'pol', 'pod', 'valid_from', 'valid_to', 'container_rates']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        result = rate_model.update(rate_id, data)
        if result.modified_count:
            return jsonify({"message": "Rate updated successfully"})
        return jsonify({"error": "Rate not found"}), 404
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error updating rate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/bulk-create', methods=['POST'])
@require_auth
def bulk_create_rates():
    try:
        rate_data = request.json
        if not rate_data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['shipping_line', 'pol_ids', 'pod_ids', 'valid_from', 'valid_to', 'container_rates']
        missing_fields = [field for field in required_fields if field not in rate_data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Validate container rates
        if not isinstance(rate_data['container_rates'], list) or not rate_data['container_rates']:
            return jsonify({"error": "Container rates must be a non-empty array"}), 400

        for rate in rate_data['container_rates']:
            if not isinstance(rate, dict) or 'type' not in rate or 'rate' not in rate:
                return jsonify({"error": "Invalid container rate format"}), 400

        # Create rates
        results = rate_model.bulk_create_rates(rate_data)
        
        return jsonify({
            "message": f"Successfully created {len(results)} rates",
            "count": len(results)
        }), 201

    except Exception as e:
        print(f"Error creating bulk rates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/<rate_id>/notes', methods=['GET'])
@require_auth
def get_rate_notes(rate_id):
    try:
        notes = rate_model.get_notes(rate_id)
        return jsonify([{
            '_id': str(note['_id']),
            'description': note['description'],
            'created_at': note['created_at'],
            'updated_at': note['updated_at']
        } for note in notes])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/<rate_id>/notes', methods=['POST'])
@require_auth
def add_rate_note(rate_id):
    try:
        data = request.json
        if not data.get('description'):
            return jsonify({"error": "Description is required"}), 400

        result = rate_model.add_note(rate_id, data)
        return jsonify({
            "message": "Note added successfully",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add logging for debugging
@rate_routes.before_request
def log_request_info():
    print(f"Request Method: {request.method}")
    print(f"Request URL: {request.url}")
    print(f"Request Headers: {request.headers}")
    if request.is_json:
        print(f"Request Data: {request.json}") 
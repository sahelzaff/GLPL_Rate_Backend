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
def get_rates():
    try:
        # Get all rates from rate model
        rates = list(db.rates.find())
        
        # Format response data
        formatted_rates = []
        for rate in rates:
            try:
                # Get related data
                shipping_line = db.shipping_lines.find_one({"_id": ObjectId(rate['shipping_line_id'])}) if 'shipping_line_id' in rate else None
                pol = db.ports.find_one({"_id": ObjectId(rate['pol_id'])}) if 'pol_id' in rate else None
                pod = db.ports.find_one({"_id": ObjectId(rate['pod_id'])}) if 'pod_id' in rate else None

                # Format rate data
                formatted_rate = {
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
                formatted_rates.append(formatted_rate)
            except Exception as e:
                print(f"Error formatting rate {rate.get('_id')}: {str(e)}")
                continue

        return jsonify({
            'status': 'success',
            'data': formatted_rates,
            'count': len(formatted_rates)
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
        if not data or not data.get('pol_code') or not data.get('pod_code'):
            return jsonify({"error": "POL and POD codes are required"}), 400

        results = rate_model.search(data['pol_code'], data['pod_code'])
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@rate_routes.route('/api/rates/bulk', methods=['POST'])
@require_auth
def create_bulk_rates():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        results = rate_model.create_bulk(data)
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
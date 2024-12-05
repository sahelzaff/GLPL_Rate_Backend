from flask import Blueprint, request, jsonify
from bson import ObjectId
from middleware.auth import require_auth, admin_required
from models.rate import Rate
from config.database import Database

rate_routes = Blueprint('rate_routes', __name__)
db = Database.get_instance().db
rate_model = Rate(db)

@rate_routes.route('/api/rates', methods=['GET'])
def get_rates():
    try:
        # Get all rates from rate model
        rates = list(rate_model.get_all())
        
        # Format response data
        formatted_rates = []
        for rate in rates:
            try:
                # Format rate data with safe gets
                formatted_rate = {
                    '_id': str(rate['_id']),
                    'shipping_line': rate.get('shipping_line', {}).get('name', 'Unknown'),
                    'shipping_line_id': str(rate.get('shipping_line_id')),
                    'pol': f"{rate.get('pol', {}).get('port_name', 'Unknown')} ({rate.get('pol', {}).get('port_code', 'Unknown')})",
                    'pol_id': str(rate.get('pol_id')),
                    'pod': f"{rate.get('pod', {}).get('port_name', 'Unknown')} ({rate.get('pod', {}).get('port_code', 'Unknown')})",
                    'pod_id': str(rate.get('pod_id')),
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
        data = request.get_json()
        if not data or not data.get('pol_code') or not data.get('pod_code'):
            return jsonify({"error": "POL and POD codes are required"}), 400

        results = rate_model.search(data['pol_code'], data['pod_code'])
        return jsonify({
            'status': 'success',
            'data': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"Error in search_rates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates', methods=['POST'])
@admin_required
def create_rate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        result = rate_model.create([data])
        return jsonify({
            'status': 'success',
            'message': 'Rate created successfully',
            'id': str(result[0])
        }), 201
    except Exception as e:
        print(f"Error in create_rate: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates/bulk', methods=['POST'])
@admin_required
def create_bulk_rates():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        results = rate_model.create_bulk(data)
        return jsonify({
            'status': 'success',
            'message': f"Successfully created {len(results)} rates",
            'ids': [str(id) for id in results]
        }), 201
    except Exception as e:
        print(f"Error in create_bulk_rates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates/<rate_id>/notes', methods=['GET'])
@admin_required
def get_rate_notes(rate_id):
    try:
        notes = rate_model.get_notes(rate_id)
        return jsonify({
            'status': 'success',
            'data': [{
                '_id': str(note['_id']),
                'description': note['description'],
                'created_at': note['created_at'],
                'updated_at': note['updated_at']
            } for note in notes],
            'count': len(notes)
        })
    except Exception as e:
        print(f"Error in get_rate_notes: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates/<rate_id>/notes', methods=['POST'])
@admin_required
def add_rate_note(rate_id):
    try:
        data = request.json
        if not data or not data.get('description'):
            return jsonify({
                'status': 'error',
                'message': 'Description is required'
            }), 400

        result = rate_model.add_note(rate_id, data)
        return jsonify({
            'status': 'success',
            'message': 'Note added successfully',
            'id': str(result.inserted_id)
        }), 201
    except Exception as e:
        print(f"Error in add_rate_note: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Add logging for debugging
@rate_routes.before_request
def log_request_info():
    print(f"Request Method: {request.method}")
    print(f"Request URL: {request.url}")
    print(f"Request Headers: {request.headers}")
    if request.is_json:
        print(f"Request Data: {request.json}") 
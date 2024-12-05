from flask import Blueprint, request, jsonify, make_response
from bson import ObjectId
from datetime import datetime
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
        rates = list(db.rates.find())
        
        # Format response data
        formatted_rates = []
        for rate in rates:
            try:
                # Safely get related data with error handling
                shipping_line_id = rate.get('shipping_line_id')
                pol_id = rate.get('pol_id')
                pod_id = rate.get('pod_id')
                
                shipping_line = None
                pol = None
                pod = None
                
                try:
                    if shipping_line_id:
                        shipping_line = db.shipping_lines.find_one({"_id": ObjectId(shipping_line_id)})
                except:
                    pass
                    
                try:
                    if pol_id:
                        pol = db.ports.find_one({"_id": ObjectId(pol_id)})
                except:
                    pass
                    
                try:
                    if pod_id:
                        pod = db.ports.find_one({"_id": ObjectId(pod_id)})
                except:
                    pass

                # Format rate data with safe gets
                formatted_rate = {
                    '_id': str(rate['_id']),
                    'shipping_line': shipping_line.get('name', 'Unknown') if shipping_line else 'Unknown',
                    'shipping_line_id': str(shipping_line_id) if shipping_line_id else None,
                    'pol': f"{pol.get('port_name', 'Unknown')} ({pol.get('port_code', 'Unknown')})" if pol else 'Unknown',
                    'pol_id': str(pol_id) if pol_id else None,
                    'pod': f"{pod.get('port_name', 'Unknown')} ({pod.get('port_code', 'Unknown')})" if pod else 'Unknown',
                    'pod_id': str(pod_id) if pod_id else None,
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

@rate_routes.route('/api/rates/bulk', methods=['POST'])
@admin_required
def create_bulk_rates():
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        results = rate_model.create_bulk(data)
        return jsonify({
            'status': 'success',
            'message': f"Successfully created {len(results)} rates",
            'count': len(results)
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
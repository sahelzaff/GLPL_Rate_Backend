from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from middleware.auth import admin_required
from config.database import Database

rate_routes = Blueprint('rate_routes', __name__)
db = Database.get_instance()
rate_model = Rate(db.db)

@rate_routes.route('/api/rates', methods=['GET'])
@admin_required
def get_rates():
    try:
        # Get all rates from rate model
        rates = list(rate_model.get_all())
        
        # Format response data
        formatted_rates = []
        for rate in rates:
            try:
                # Get shipping line details
                shipping_line = db.db.shipping_lines.find_one({'_id': rate.get('shipping_line_id')})
                pol = db.db.ports.find_one({'_id': rate.get('pol_id')})
                pod = db.db.ports.find_one({'_id': rate.get('pod_id')})

                # Format rate data with safe gets
                formatted_rate = {
                    '_id': str(rate['_id']),
                    'shipping_line': shipping_line.get('name', 'Unknown') if shipping_line else 'Unknown',
                    'shipping_line_id': str(rate.get('shipping_line_id')),
                    'pol': f"{pol.get('port_name', 'Unknown')} ({pol.get('port_code', 'Unknown')})" if pol else 'Unknown',
                    'pol_id': str(rate.get('pol_id')),
                    'pod': f"{pod.get('port_name', 'Unknown')} ({pod.get('port_code', 'Unknown')})" if pod else 'Unknown',
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

@rate_routes.route('/api/rates/<rate_id>', methods=['PUT'])
@admin_required
def update_rate(rate_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Clean and prepare data
        update_data = {
            'shipping_line_id': ObjectId(data['shipping_line']),
            'pol_id': ObjectId(data['pol']),
            'pod_id': ObjectId(data['pod']),
            'valid_from': data['valid_from'],
            'valid_to': data['valid_to'],
            'container_rates': [],
            'updated_at': datetime.utcnow()
        }

        # Process container rates
        for rate in data['container_rates']:
            base_rate = float(rate.get('base_rate', 0))
            ewrs_laden = float(rate.get('ewrs_laden', 0))
            ewrs_empty = float(rate.get('ewrs_empty', 0))
            baf = float(rate.get('baf', 0))
            reefer_surcharge = float(rate.get('reefer_surcharge', 0))

            container_rate = {
                'type': rate['type'],
                'base_rate': base_rate,
                'ewrs_laden': ewrs_laden,
                'ewrs_empty': ewrs_empty,
                'baf': baf,
                'reefer_surcharge': reefer_surcharge,
                'rate': base_rate + ewrs_laden + ewrs_empty + baf + reefer_surcharge,
                'total_cost': base_rate + ewrs_laden + ewrs_empty + baf + reefer_surcharge
            }
            update_data['container_rates'].append(container_rate)

        result = rate_model.update(rate_id, update_data)
        if result.modified_count:
            return jsonify({
                'status': 'success',
                'message': 'Rate updated successfully'
            })
        return jsonify({
            'status': 'error',
            'message': 'Rate not found or no changes made'
        }), 404

    except Exception as e:
        print(f"Error updating rate: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@rate_routes.route('/api/rates/<rate_id>', methods=['DELETE'])
@admin_required
def delete_rate(rate_id):
    try:
        result = rate_model.delete(rate_id)
        if result.deleted_count:
            return jsonify({
                'status': 'success',
                'message': 'Rate deleted successfully'
            })
        return jsonify({
            'status': 'error',
            'message': 'Rate not found'
        }), 404
    except Exception as e:
        print(f"Error deleting rate: {str(e)}")
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

        # Create rates for each POL-POD combination
        results = []
        for pol_id in data['pol_ids']:
            for pod_id in data['pod_ids']:
                single_rate = {
                    'shipping_line': data['shipping_line'],
                    'pol': pol_id,
                    'pod': pod_id,
                    'valid_from': data['valid_from'],
                    'valid_to': data['valid_to'],
                    'container_rates': data['container_rates'],
                    'notes': data.get('notes', [])
                }
                result = rate_model.create(single_rate)
                results.append(result)

        return jsonify({
            'status': 'success',
            'message': f'Successfully created {len(results)} rates',
            'ids': [str(result.inserted_id) for result in results]
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
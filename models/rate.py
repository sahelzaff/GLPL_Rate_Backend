from bson import ObjectId
from datetime import datetime
import traceback

class Rate:
    def __init__(self, db):
        """Initialize Rate model with database instance"""
        self.db = db  # Store the database instance
        self.collection = db.rates
        self.history_collection = db.rate_history
        self.notes_collection = db.rate_notes
        self.shipping_lines = db.shipping_lines
        self.ports = db.ports

    def get_all(self):
        """Get all rates with populated shipping line and port information"""
        pipeline = [
            {
                '$lookup': {
                    'from': 'shipping_lines',
                    'localField': 'shipping_line_id',
                    'foreignField': '_id',
                    'as': 'shipping_line'
                }
            },
            {
                '$lookup': {
                    'from': 'ports',
                    'localField': 'pol_id',
                    'foreignField': '_id',
                    'as': 'pol'
                }
            },
            {
                '$lookup': {
                    'from': 'ports',
                    'localField': 'pod_id',
                    'foreignField': '_id',
                    'as': 'pod'
                }
            },
            {
                '$unwind': {
                    'path': '$shipping_line',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$unwind': {
                    'path': '$pol',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$unwind': {
                    'path': '$pod',
                    'preserveNullAndEmptyArrays': True
                }
            }
        ]
        return self.collection.aggregate(pipeline)

    def create(self, rate_data):
        try:
            # Validate required fields
            required_fields = ['shipping_line', 'pol', 'pod', 'valid_from', 'valid_to', 'container_rates']
            for field in required_fields:
                if field not in rate_data:
                    raise ValueError(f"Missing required field: {field}")

            # Clean and prepare data
            cleaned_data = {
                'shipping_line_id': ObjectId(rate_data['shipping_line']),
                'pol_id': ObjectId(rate_data['pol']),
                'pod_id': ObjectId(rate_data['pod']),
                'valid_from': rate_data['valid_from'],
                'valid_to': rate_data['valid_to'],
                'container_rates': [],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            # Process container rates
            for rate in rate_data['container_rates']:
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
                cleaned_data['container_rates'].append(container_rate)

            # Insert the rate
            result = self.collection.insert_one(cleaned_data)

            # Add notes if present
            if 'notes' in rate_data and rate_data['notes']:
                for note in rate_data['notes']:
                    if note.get('description'):
                        self.notes_collection.insert_one({
                            'rate_id': result.inserted_id,
                            'description': note['description'],
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        })

            # Create history record
            history_data = {
                'rate_id': result.inserted_id,
                'shipping_line_id': cleaned_data['shipping_line_id'],
                'pol_id': cleaned_data['pol_id'],
                'pod_id': cleaned_data['pod_id'],
                'container_rates': cleaned_data['container_rates'],
                'valid_from': cleaned_data['valid_from'],
                'valid_to': cleaned_data['valid_to'],
                'created_at': datetime.utcnow()
            }
            self.history_collection.insert_one(history_data)

            return result

        except Exception as e:
            print(f"Error creating rate: {str(e)}")
            raise

    def update(self, rate_id, update_data):
        try:
            # Create history record before update
            old_rate = self.collection.find_one({'_id': ObjectId(rate_id)})
            if old_rate:
                history_data = {
                    'rate_id': old_rate['_id'],
                    'shipping_line_id': old_rate['shipping_line_id'],
                    'pol_id': old_rate['pol_id'],
                    'pod_id': old_rate['pod_id'],
                    'container_rates': old_rate['container_rates'],
                    'valid_from': old_rate['valid_from'],
                    'valid_to': old_rate['valid_to'],
                    'created_at': datetime.utcnow()
                }
                self.history_collection.insert_one(history_data)

            # Update the rate
            result = self.collection.update_one(
                {'_id': ObjectId(rate_id)},
                {'$set': update_data}
            )
            return result
        except Exception as e:
            print(f"Error updating rate: {str(e)}")
            raise

    def delete(self, rate_id):
        try:
            # Delete associated notes first
            self.notes_collection.delete_many({'rate_id': ObjectId(rate_id)})
            
            # Delete the rate
            result = self.collection.delete_one({'_id': ObjectId(rate_id)})
            return result
        except Exception as e:
            print(f"Error deleting rate: {str(e)}")
            raise

    def get_notes(self, rate_id):
        try:
            return list(self.notes_collection.find({
                'rate_id': ObjectId(rate_id)
            }).sort('created_at', -1))
        except Exception as e:
            print(f"Error getting notes: {str(e)}")
            raise

    def add_note(self, rate_id, note_data):
        try:
            note = {
                'rate_id': ObjectId(rate_id),
                'description': note_data['description'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            return self.notes_collection.insert_one(note)
        except Exception as e:
            print(f"Error adding note: {str(e)}")
            raise

    def search(self, pol_code, pod_code):
        """Search rates by POL and POD codes"""
        try:
            print(f"Searching for rates with POL: {pol_code}, POD: {pod_code}")
            
            # Get port IDs from codes using ports collection
            pol = self.ports.find_one({"port_code": pol_code.upper()})
            pod = self.ports.find_one({"port_code": pod_code.upper()})
            
            print(f"Found POL: {pol}")
            print(f"Found POD: {pod}")
            
            if not pol or not pod:
                return {
                    "status": "success",
                    "data": [],
                    "message": "No rates found for given ports"
                }

            # Build pipeline to get rates with populated references
            pipeline = [
                {
                    '$match': {
                        'pol_id': pol['_id'],
                        'pod_id': pod['_id']
                    }
                },
                {
                    '$lookup': {
                        'from': 'shipping_lines',
                        'localField': 'shipping_line_id',
                        'foreignField': '_id',
                        'as': 'shipping_line'
                    }
                },
                {
                    '$unwind': '$shipping_line'
                },
                {
                    '$lookup': {
                        'from': 'ports',
                        'localField': 'pol_id',
                        'foreignField': '_id',
                        'as': 'pol'
                    }
                },
                {
                    '$unwind': '$pol'
                },
                {
                    '$lookup': {
                        'from': 'ports',
                        'localField': 'pod_id',
                        'foreignField': '_id',
                        'as': 'pod'
                    }
                },
                {
                    '$unwind': '$pod'
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            print(f"Found {len(results)} results")
            
            # Format the results
            formatted_results = []
            for rate in results:
                try:
                    print(f"Processing rate: {rate}")
                    # Format container rates - handle both formats
                    container_rates = []
                    for cr in rate['container_rates']:
                        try:
                            # Check which format the rate is in
                            if isinstance(cr.get('rate'), (int, float)):
                                # Handle simple numeric rate
                                rate_value = cr['rate']
                                container_rate = {
                                    'type': cr['type'],
                                    'base_rate': rate_value,
                                    'ewrs_laden': 0,
                                    'ewrs_empty': 0,
                                    'baf': 0,
                                    'reefer_surcharge': 0,
                                    'total': rate_value
                                }
                                container_rates.append(container_rate)
                            elif isinstance(cr.get('rate'), dict) and '$numberInt' in cr['rate']:
                                # Handle MongoDB NumberInt format
                                rate_value = int(cr['rate']['$numberInt'])
                                container_rate = {
                                    'type': cr['type'],
                                    'base_rate': rate_value,
                                    'ewrs_laden': 0,
                                    'ewrs_empty': 0,
                                    'baf': 0,
                                    'reefer_surcharge': 0,
                                    'total': rate_value
                                }
                                container_rates.append(container_rate)
                            elif 'base_rate' in cr:
                                # Handle detailed rate format
                                container_rate = {
                                    'type': cr['type'],
                                    'base_rate': cr.get('base_rate', 0),
                                    'ewrs_laden': cr.get('ewrs_laden', 0),
                                    'ewrs_empty': cr.get('ewrs_empty', 0),
                                    'baf': cr.get('baf', 0),
                                    'reefer_surcharge': cr.get('reefer_surcharge', 0),
                                    'total': cr.get('total_cost', 
                                                  sum([cr.get('base_rate', 0),
                                                       cr.get('ewrs_laden', 0),
                                                       cr.get('ewrs_empty', 0),
                                                       cr.get('baf', 0),
                                                       cr.get('reefer_surcharge', 0)]))
                                }
                                container_rates.append(container_rate)
                        except Exception as e:
                            print(f"Error processing container rate: {e}")
                            print(f"Container rate data: {cr}")
                            continue

                    if container_rates:  # Only add the rate if it has valid container rates
                        formatted_rate = {
                            '_id': str(rate['_id']),
                            'shipping_line': rate['shipping_line']['name'],
                            'pol': f"{rate['pol']['port_name']} ({rate['pol']['port_code']})",
                            'pod': f"{rate['pod']['port_name']} ({rate['pod']['port_code']})",
                            'valid_from': rate['valid_from'],
                            'valid_to': rate['valid_to'],
                            'container_rates': container_rates,
                            'created_at': rate['created_at'],
                            'updated_at': rate['updated_at']
                        }
                        formatted_results.append(formatted_rate)
                except Exception as e:
                    print(f"Error formatting rate: {e}")
                    print(f"Rate data: {rate}")
                    continue

            return {
                "status": "success",
                "data": formatted_results,
                "message": f"Found {len(formatted_results)} rates"
            }

        except Exception as e:
            print(f"Error in rate search: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": str(e),
                "data": []
            }
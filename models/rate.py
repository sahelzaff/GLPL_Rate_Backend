from bson import ObjectId
from datetime import datetime

class Rate:
    def __init__(self, db):
        self.collection = db.rates
        self.history_collection = db.rate_history
        self.notes_collection = db.rate_notes
        self.shipping_lines = db.shipping_lines
        self.ports = db.ports

    def get_all(self):
        try:
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
        except Exception as e:
            print(f"Error in get_all: {str(e)}")
            raise

    def search(self, pol_code, pod_code):
        try:
            # Find ports by their codes
            pol = self.ports.find_one({"port_code": pol_code.upper()})
            pod = self.ports.find_one({"port_code": pod_code.upper()})

            if not pol or not pod:
                return []

            # Get rates using port IDs
            pipeline = [
                {
                    '$match': {
                        'pol_id': pol['_id'],
                        'pod_id': pod['_id'],
                        'valid_to': {'$gte': datetime.utcnow()}
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
                }
            ]

            rates = list(self.collection.aggregate(pipeline))
            
            # Format rates for response
            formatted_rates = []
            for rate in rates:
                formatted_rate = {
                    'shipping_line': rate['shipping_line']['name'],
                    'pol': f"{pol['port_name']} ({pol['port_code']})",
                    'pod': f"{pod['port_name']} ({pod['port_code']})",
                    'valid_from': rate['valid_from'],
                    'valid_to': rate['valid_to'],
                    'container_rates': rate['container_rates']
                }
                formatted_rates.append(formatted_rate)

            return formatted_rates
        except Exception as e:
            print(f"Error in search: {str(e)}")
            raise

    def create_bulk(self, rates_data):
        try:
            # Validate and clean data
            for rate in rates_data:
                if not all(k in rate for k in ['shipping_line_id', 'pol_id', 'pod_id', 'container_rates']):
                    raise ValueError("Missing required fields")
                
                # Convert IDs to ObjectId
                rate['shipping_line_id'] = ObjectId(rate['shipping_line_id'])
                rate['pol_id'] = ObjectId(rate['pol_id'])
                rate['pod_id'] = ObjectId(rate['pod_id'])
                
                # Add timestamps
                rate['created_at'] = datetime.utcnow()
                rate['updated_at'] = datetime.utcnow()

            # Insert rates
            result = self.collection.insert_many(rates_data)
            return result.inserted_ids
        except Exception as e:
            print(f"Error in create_bulk: {str(e)}")
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
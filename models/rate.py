from bson import ObjectId
from datetime import datetime

class Rate:
    def __init__(self, db):
        self.collection = db.rates
        self.history_collection = db.rate_history
        self.notes_collection = db.rate_notes

    def get_all(self):
        try:
            # Return all rates sorted by creation date
            return self.collection.find().sort('created_at', -1)
        except Exception as e:
            print(f"Error in get_all: {str(e)}")
            raise

    def search(self, pol_code, pod_code):
        try:
            # Find ports by their codes
            pol = self.db.ports.find_one({"port_code": pol_code.upper()})
            pod = self.db.ports.find_one({"port_code": pod_code.upper()})

            if not pol or not pod:
                return []

            # Get rates using port IDs
            rates = list(self.collection.find({
                "pol_id": pol['_id'],
                "pod_id": pod['_id']
            }))

            # Populate with shipping line details
            populated_rates = []
            for rate in rates:
                shipping_line = self.db.shipping_lines.find_one({"_id": rate['shipping_line_id']})
                populated_rate = {
                    'shipping_line': shipping_line['name'] if shipping_line else 'Unknown',
                    'pol': f"{pol['port_name']} ({pol['port_code']})",
                    'pod': f"{pod['port_name']} ({pod['port_code']})",
                    'valid_from': rate['valid_from'],
                    'valid_to': rate['valid_to'],
                    'container_rates': rate['container_rates']
                }
                populated_rates.append(populated_rate)

            return populated_rates
        except Exception as e:
            print(f"Error in search: {str(e)}")
            raise

    def create_bulk(self, rates_data):
        try:
            results = []
            for rate_entry in rates_data:
                # Add timestamps
                rate_entry['created_at'] = datetime.utcnow()
                rate_entry['updated_at'] = datetime.utcnow()
                
                # Insert the rate
                result = self.collection.insert_one(rate_entry)
                results.append(result)
                
                # Create history record
                history_data = {
                    'rate_id': result.inserted_id,
                    'shipping_line_id': rate_entry['shipping_line_id'],
                    'pol_id': rate_entry['pol_id'],
                    'pod_id': rate_entry['pod_id'],
                    'container_rates': rate_entry['container_rates'],
                    'valid_from': rate_entry['valid_from'],
                    'valid_to': rate_entry['valid_to'],
                    'created_at': datetime.utcnow()
                }
                self.history_collection.insert_one(history_data)
            
            return results
        except Exception as e:
            print(f"Error in create_bulk: {str(e)}")
            raise

    def get_notes(self, rate_id):
        try:
            return list(self.notes_collection.find({'rate_id': ObjectId(rate_id)}))
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
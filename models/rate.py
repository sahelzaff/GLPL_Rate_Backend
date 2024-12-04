from bson import ObjectId
from datetime import datetime

class Rate:
    def __init__(self, db):
        self.collection = db.rates
        self.history_collection = db.rate_history
        self.notes_collection = db.rate_notes

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
                'container_rates': rate_data['container_rates'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            result = self.collection.insert_one(cleaned_data)
            return result
        except Exception as e:
            print(f"Error in create: {str(e)}")
            raise

    def get_all(self):
        try:
            cursor = self.collection.find().sort('created_at', -1)
            rates = []
            
            for rate in cursor:
                try:
                    # Convert ObjectIds to strings
                    rate['_id'] = str(rate['_id'])
                    rate['shipping_line_id'] = str(rate['shipping_line_id'])
                    rate['pol_id'] = str(rate['pol_id'])
                    rate['pod_id'] = str(rate['pod_id'])
                    
                    # Ensure container_rates exists
                    if 'container_rates' not in rate:
                        rate['container_rates'] = []
                        
                    rates.append(rate)
                except Exception as e:
                    print(f"Error processing rate: {str(e)}")
                    continue
                    
            return rates
        except Exception as e:
            print(f"Error in get_all: {str(e)}")
            return []

    def find_by_id(self, rate_id):
        return self.collection.find_one({"_id": ObjectId(rate_id)})

    def update(self, rate_id, update_data):
        try:
            cleaned_data = {
                'shipping_line_id': ObjectId(update_data['shipping_line']),
                'pol_id': ObjectId(update_data['pol']),
                'pod_id': ObjectId(update_data['pod']),
                'valid_from': update_data['valid_from'],
                'valid_to': update_data['valid_to'],
                'container_rates': update_data['container_rates'],
                'updated_at': datetime.utcnow()
            }

            return self.collection.update_one(
                {"_id": ObjectId(rate_id)},
                {"$set": cleaned_data}
            )
        except Exception as e:
            print(f"Error in update: {str(e)}")
            raise

    def delete(self, rate_id):
        try:
            return self.collection.delete_one({"_id": ObjectId(rate_id)})
        except Exception as e:
            print(f"Error in delete: {str(e)}")
            raise

    def search_rates(self, pol_id, pod_id, valid_date=None):
        query = {
            "pol_id": ObjectId(pol_id),
            "pod_id": ObjectId(pod_id)
        }
        
        if valid_date:
            query.update({
                "valid_from": {"$lte": valid_date},
                "valid_to": {"$gte": valid_date}
            })
            
        return self.collection.find(query)

    def get_rate_history(self, rate_id):
        return self.history_collection.find(
            {"rate_id": ObjectId(rate_id)}
        ).sort("updated_at", -1)

    def bulk_create(self, rates_data, updated_by):
        results = []
        for rate_data in rates_data:
            rate_data['created_at'] = datetime.utcnow()
            rate_data['last_updated'] = datetime.utcnow()
            rate_data['updated_by'] = updated_by
            results.append(self.create(rate_data))
        return results

    def bulk_create_rates(self, rate_data):
        """
        Create rates for all POL-POD combinations
        """
        try:
            results = []
            pol_ids = rate_data.get('pol_ids', [])
            pod_ids = rate_data.get('pod_ids', [])
            
            # Create a rate for each POL-POD combination
            for pol_id in pol_ids:
                for pod_id in pod_ids:
                    rate_entry = {
                        'shipping_line_id': ObjectId(rate_data['shipping_line']),
                        'pol_id': ObjectId(pol_id),
                        'pod_id': ObjectId(pod_id),
                        'valid_from': rate_data['valid_from'],
                        'valid_to': rate_data['valid_to'],
                        'container_rates': rate_data['container_rates'],
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                    
                    # Insert the rate
                    result = self.collection.insert_one(rate_entry)
                    
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
                    
                    results.append(result)
                    
            return results
        except Exception as e:
            print(f"Error creating bulk rates: {str(e)}")
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

    def get_notes(self, rate_id):
        try:
            return list(self.notes_collection.find({'rate_id': ObjectId(rate_id)}))
        except Exception as e:
            print(f"Error getting notes: {str(e)}")
            raise
from bson import ObjectId
from datetime import datetime

class Port:
    def __init__(self, db):
        self.collection = db.ports

    def get_all(self):
        return self.collection.find()

    def create(self, port_data):
        # Ensure required fields are present and not null
        required_fields = ['port_code', 'port_name', 'country']
        for field in required_fields:
            if not port_data.get(field):
                raise ValueError(f"{field} is required and cannot be empty")

        # Clean the data before insertion
        cleaned_data = {
            'port_code': port_data['port_code'].upper(),
            'port_name': port_data['port_name'],
            'country': port_data['country'],
            'region': port_data.get('region', ''),  # Default to empty string if not provided
            'created_at': datetime.utcnow()
        }
        
        return self.collection.insert_one(cleaned_data)

    def find_by_id(self, port_id):
        return self.collection.find_one({"_id": ObjectId(port_id)})

    def find_by_code(self, port_code):
        return self.collection.find_one({"port_code": port_code.upper()})

    def update(self, port_id, update_data):
        # Clean the update data
        cleaned_data = {}
        if 'port_code' in update_data:
            cleaned_data['port_code'] = update_data['port_code'].upper()
        if 'port_name' in update_data:
            cleaned_data['port_name'] = update_data['port_name']
        if 'country' in update_data:
            cleaned_data['country'] = update_data['country']
        if 'region' in update_data:
            cleaned_data['region'] = update_data['region'] or ''  # Convert null to empty string
        
        cleaned_data['updated_at'] = datetime.utcnow()

        return self.collection.update_one(
            {"_id": ObjectId(port_id)},
            {"$set": cleaned_data}
        )

    def delete(self, port_id):
        return self.collection.delete_one({"_id": ObjectId(port_id)})

    def search(self, query):
        return self.collection.find({
            "$or": [
                {"port_name": {"$regex": query, "$options": "i"}},
                {"port_code": {"$regex": query, "$options": "i"}},
                {"country": {"$regex": query, "$options": "i"}}
            ]
        }) 
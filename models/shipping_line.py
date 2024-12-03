from bson import ObjectId
from datetime import datetime

class ShippingLine:
    def __init__(self, db):
        self.collection = db.shipping_lines

    def get_all(self):
        return self.collection.find()

    def create(self, shipping_line_data):
        # Ensure required fields are present
        required_fields = ['name', 'contact_email']
        for field in required_fields:
            if not shipping_line_data.get(field):
                raise ValueError(f"{field} is required and cannot be empty")

        # Clean and prepare data
        cleaned_data = {
            'name': shipping_line_data['name'].strip(),
            'contact_email': shipping_line_data['contact_email'].strip().lower(),
            'website': shipping_line_data.get('website', '').strip(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return self.collection.insert_one(cleaned_data)

    def find_by_id(self, line_id):
        return self.collection.find_one({"_id": ObjectId(line_id)})

    def find_by_name(self, name):
        return self.collection.find_one({"name": name})

    def update(self, line_id, update_data):
        # Clean the update data
        cleaned_data = {}
        if 'name' in update_data:
            cleaned_data['name'] = update_data['name'].strip()
        if 'contact_email' in update_data:
            cleaned_data['contact_email'] = update_data['contact_email'].strip().lower()
        if 'website' in update_data:
            cleaned_data['website'] = update_data['website'].strip()
        
        cleaned_data['updated_at'] = datetime.utcnow()

        return self.collection.update_one(
            {"_id": ObjectId(line_id)},
            {"$set": cleaned_data}
        )

    def delete(self, line_id):
        return self.collection.delete_one({"_id": ObjectId(line_id)})

    def search(self, query):
        return self.collection.find({
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"contact_email": {"$regex": query, "$options": "i"}}
            ]
        }) 
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

class Database:
    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._client is None:
            self.initialize_connection()

    def initialize_connection(self):
        MONGO_URI = "mongodb+srv://goodrichlogisticsmobile:1HEKHz1CM56clIDE@cluster0.7a6zw.mongodb.net/test?retryWrites=true&w=majority"
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            self._client.admin.command('ping')
            self._db = self._client.test
            print("Successfully connected to MongoDB!")
            self._create_indexes()
        except ServerSelectionTimeoutError as e:
            print(f"Failed to connect to MongoDB: Connection timed out - {e}")
            raise
        except OperationFailure as e:
            print(f"MongoDB operation failed: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    def _create_indexes(self):
        try:
            # Ports indexes
            self._db.ports.create_index([("port_code", 1)], unique=True)
            self._db.ports.create_index([("port_name", 1)])
            # Remove the problematic compound index if it exists
            try:
                self._db.ports.drop_index("name_1_region_1")
            except:
                pass
            
            # Shipping lines indexes
            self._db.shipping_lines.create_index([("name", 1)], unique=True)
            
            # Rates indexes
            self._db.rates.create_index([
                ("pol_id", 1),
                ("pod_id", 1),
                ("shipping_line_id", 1),
                ("valid_from", 1),
                ("valid_to", 1)
            ])
            
            # Indexes for rate notes
            self._db.rate_notes.create_index([("rate_id", 1)])
            self._db.rate_notes.create_index([("created_at", -1)])
            
            # Additional indexes for rates
            self._db.rates.create_index([
                ("shipping_line_id", 1),
                ("pol_id", 1),
                ("pod_id", 1),
                ("valid_from", 1),
                ("valid_to", 1),
                ("container_rates.type", 1)
            ])
            
            print("Database indexes created successfully")
        except Exception as e:
            print(f"Error creating indexes: {e}")

    @property
    def db(self):
        if self._client is None:
            self.initialize_connection()
        return self._db

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
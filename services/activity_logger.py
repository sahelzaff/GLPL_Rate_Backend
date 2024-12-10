import redis
import json
from datetime import datetime
import pytz
from config.database import Database
from bson import ObjectId
import os

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ActivityLogger:
    _instance = None
    REDIS_KEY = 'admin_activities'
    REDIS_LIST_MAX_LENGTH = 100
    TIMEZONE = pytz.timezone('Asia/Kolkata')
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.db = Database.get_instance().db
        
        # Railway.app Redis connection details
        REDIS_URL = "redis://default:YCNmYklVCdzfCmpMymNXyhBVovpoXEdp@autorack.proxy.rlwy.net:28674"  # Replace with your actual Redis URL
        # REDIS_URL = "redis://localhost:6379"  # Replace with your actual Redis URL
        
        try:
            self.redis = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis.ping()
            print("Successfully connected to Redis on Railway.app!")
            # self.redis.ping()
            # print("Successfully connected to Redis on Local Redis!")
            self.redis_available = True
        except redis.ConnectionError as e:
            print(f"Warning: Redis connection failed: {str(e)}")
            print("Falling back to MongoDB only.")
            self.redis_available = False
        except Exception as e:
            print(f"Unexpected error connecting to Redis: {str(e)}")
            self.redis_available = False

    def log_activity(self, activity_type, data, user=None):
        try:
            # Get current time in Indian timezone
            current_time = datetime.now(self.TIMEZONE)
            
            activity = {
                'type': activity_type,
                'data': data,
                'timestamp': current_time.isoformat(),
                'user': {
                    'id': str(user['_id']) if user else None,
                    'name': user.get('name', 'System'),
                    'email': user.get('email', 'system@glpl.com')
                } if user else None
            }
            
            # Store in MongoDB for persistence
            mongo_activity = activity.copy()
            mongo_activity['timestamp'] = current_time
            result = self.db.admin_activities.insert_one(mongo_activity)
            
            activity['_id'] = str(result.inserted_id)
            
            if self.redis_available:
                try:
                    # Store in Redis with retry mechanism
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            self.redis.lpush(self.REDIS_KEY, json.dumps(activity, cls=JSONEncoder))
                            self.redis.ltrim(self.REDIS_KEY, 0, self.REDIS_LIST_MAX_LENGTH - 1)
                            break
                        except redis.ConnectionError:
                            if attempt == max_retries - 1:
                                raise
                            print(f"Redis connection failed, attempt {attempt + 1} of {max_retries}")
                            continue
                except redis.RedisError as e:
                    print(f"Warning: Failed to store activity in Redis: {str(e)}")
                    # Redis operation failed, but MongoDB operation succeeded
                    # We can continue without Redis
            
        except Exception as e:
            print(f"Error logging activity: {str(e)}")
            raise

    def get_recent_activities(self, limit=20):
        try:
            if self.redis_available:
                try:
                    activities = []
                    raw_activities = self.redis.lrange(self.REDIS_KEY, 0, limit - 1)
                    
                    for raw_activity in raw_activities:
                        activity = json.loads(raw_activity)
                        # Convert UTC timestamp to Indian timezone
                        timestamp = datetime.fromisoformat(activity['timestamp'])
                        if timestamp.tzinfo is None:
                            timestamp = pytz.utc.localize(timestamp)
                        activity['timestamp'] = timestamp.astimezone(self.TIMEZONE).isoformat()
                        activities.append(activity)
                    
                    if activities:
                        return activities
                except redis.RedisError as e:
                    print(f"Warning: Failed to fetch activities from Redis: {str(e)}")
            
            return self.get_historical_activities(limit=limit)
            
        except Exception as e:
            print(f"Error fetching recent activities: {str(e)}")
            return []

    def get_historical_activities(self, skip=0, limit=50, start_date=None, end_date=None):
        try:
            query = {}
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            activities = list(self.db.admin_activities.find(
                query,
                skip=skip,
                limit=limit
            ).sort('timestamp', -1))
            
            formatted_activities = []
            for activity in activities:
                # Convert UTC timestamp to Indian timezone
                timestamp = activity['timestamp']
                if timestamp.tzinfo is None:
                    timestamp = pytz.utc.localize(timestamp)
                activity['timestamp'] = timestamp.astimezone(self.TIMEZONE).isoformat()
                activity['_id'] = str(activity['_id'])
                formatted_activities.append(activity)
            
            return formatted_activities
        except Exception as e:
            print(f"Error fetching historical activities: {str(e)}")
            return []

    def format_activity_description(self, activity):
        """Generate human-readable description for an activity."""
        try:
            if activity['type'] == 'user_created':
                return f"New user {activity['data']['user_details']['name']} ({activity['data']['user_details']['role']}) was created"
            elif activity['type'] == 'user_updated':
                return f"User {activity['data']['original']['name']} was updated"
            elif activity['type'] == 'user_deleted':
                return f"User {activity['data']['user_details']['name']} was deleted"
            elif activity['type'] == 'port_created':
                return f"New port {activity['data']['port_details']['port_name']} ({activity['data']['port_details']['port_code']}) was added"
            elif activity['type'] == 'port_updated':
                return f"Port {activity['data']['original']['port_name']} was updated"
            elif activity['type'] == 'port_deleted':
                return f"Port {activity['data']['port_details']['port_name']} was deleted"
            elif activity['type'] == 'rate_created':
                return f"New rate was added for {activity['data']['rate_details']['pol']} to {activity['data']['rate_details']['pod']}"
            elif activity['type'] == 'rate_updated':
                return f"Rate was updated for {activity['data']['original']['pol']} to {activity['data']['original']['pod']}"
            elif activity['type'] == 'rate_deleted':
                return f"Rate was deleted for {activity['data']['rate_details']['pol']} to {activity['data']['rate_details']['pod']}"
            elif activity['type'] == 'user_login':
                return f"User {activity['data']['user_email']} logged in"
            elif activity['type'] == 'user_logout':
                return f"User {activity['data']['user_email']} logged out"
            return "Unknown activity"
        except Exception:
            return "Activity description unavailable"
            
# Create singleton instance
activity_logger = ActivityLogger.get_instance() 
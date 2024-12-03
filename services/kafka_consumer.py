from confluent_kafka import Consumer, KafkaError
import json
from config.database import Database
from datetime import datetime

class KafkaConsumer:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'glpl_rate_admin_group',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(['admin_activities'])
        self.db = Database.get_instance().db
        
    def store_activity(self, event):
        try:
            # Store the activity in MongoDB
            self.db.admin_activities.insert_one({
                'type': event['type'],
                'data': event['data'],
                'timestamp': datetime.fromisoformat(event['timestamp']),
                'user': event['user']
            })
        except Exception as e:
            print(f"Error storing activity: {str(e)}")
            
    def start_consuming(self):
        try:
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Consumer error: {msg.error()}")
                        break
                        
                try:
                    event = json.loads(msg.value().decode('utf-8'))
                    self.store_activity(event)
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close() 
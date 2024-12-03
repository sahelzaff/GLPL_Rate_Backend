from confluent_kafka import Producer
import json
from datetime import datetime

class KafkaProducer:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.producer = Producer({
            'bootstrap.servers': 'localhost:9092',
            'client.id': 'glpl_rate_admin_producer'
        })
        
    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')
            
    def produce_event(self, event_type, data, user=None):
        try:
            event = {
                'type': event_type,
                'data': data,
                'timestamp': datetime.utcnow().isoformat(),
                'user': {
                    'id': str(user['_id']) if user else None,
                    'name': user.get('name', 'System'),
                    'email': user.get('email', 'system@glpl.com')
                } if user else None
            }
            
            self.producer.produce(
                'admin_activities',
                key=event_type,
                value=json.dumps(event).encode('utf-8'),
                callback=self.delivery_report
            )
            self.producer.flush()
            
        except Exception as e:
            print(f"Error producing Kafka event: {str(e)}")
            
kafka_producer = KafkaProducer.get_instance() 
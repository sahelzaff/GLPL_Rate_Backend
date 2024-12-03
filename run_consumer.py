from services.kafka_consumer import KafkaConsumer

if __name__ == '__main__':
    print("Starting Kafka consumer...")
    consumer = KafkaConsumer()
    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping consumer...") 
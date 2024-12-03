from pymongo import MongoClient
from datetime import datetime, timedelta

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://goodrichlogisticsmobile:1HEKHz1CM56clIDE@cluster0.7a6zw.mongodb.net/glpl_rate_db?retryWrites=true&w=majority"
try:
    # Connect with retry mechanism
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Force a connection to verify it works
    client.server_info()
    print("Successfully connected to MongoDB Atlas!")
    
    db = client['glpl_rate_db']

    # Clear existing collections
    try:
        db.shippingLines.drop()
        db.ports.drop()
        db.containers.drop()
        db.rates.drop()
    except Exception as e:
        print(f"Warning during collection drop: {e}")

    # Insert shipping lines
    shipping_lines = [
        {"_id": "1", "name": "COSCO", "details": "Global shipping line"},
        {"_id": "2", "name": "MSC", "details": "Mediterranean Shipping Company"},
        {"_id": "3", "name": "Maersk", "details": "Maersk Line"}
    ]
    db.shippingLines.insert_many(shipping_lines)
    print("Inserted shipping lines")

    # Insert ports
    ports = [
        {"_id": "1", "name": "Mundra", "region": "India"},
        {"_id": "2", "name": "Nhava Sheva", "region": "India"},
        {"_id": "3", "name": "Singapore", "region": "Singapore"},
        {"_id": "4", "name": "Rotterdam", "region": "Netherlands"}
    ]
    db.ports.insert_many(ports)
    print("Inserted ports")

    # Insert containers
    containers = [
        {"_id": "1", "type": "20", "description": "Standard container"},
        {"_id": "2", "type": "40", "description": "Standard container"},
        {"_id": "3", "type": "45", "description": "Highcube container"},
        {"_id": "4", "type": "40", "description": "Reefer container"}
    ]
    db.containers.insert_many(containers)

    # Insert rates
    current_date = datetime.now()
    rates = [
        {
            "_id": "1",
            "shippingLineId": "1",
            "polId": "1",
            "podId": "3",
            "containerRates": [
                {"containerId": "1", "rate": 3200},
                {"containerId": "2", "rate": 3900},
                {"containerId": "3", "rate": 4200}
            ],
            "validityFrom": current_date.strftime("%Y-%m-%d"),
            "validityTo": (current_date + timedelta(days=14)).strftime("%Y-%m-%d"),
            "remarks": "Direct service"
        },
        {
            "_id": "2",
            "shippingLineId": "2",
            "polId": "1",
            "podId": "3",
            "containerRates": [
                {"containerId": "1", "rate": 3100},
                {"containerId": "2", "rate": 3800},
                {"containerId": "4", "rate": 4500}
            ],
            "validityFrom": current_date.strftime("%Y-%m-%d"),
            "validityTo": (current_date + timedelta(days=14)).strftime("%Y-%m-%d"),
            "remarks": "Weekly service"
        },
        {
            "_id": "3",
            "shippingLineId": "3",
            "polId": "2",
            "podId": "4",
            "containerRates": [
                {"containerId": "1", "rate": 4200},
                {"containerId": "2", "rate": 4900},
                {"containerId": "3", "rate": 5200}
            ],
            "validityFrom": current_date.strftime("%Y-%m-%d"),
            "validityTo": (current_date + timedelta(days=14)).strftime("%Y-%m-%d"),
            "remarks": "Direct service via Singapore"
        }
    ]
    db.rates.insert_many(rates)

    print("Database initialized with sample data!")
    
except Exception as e:
    print(f"Error connecting to MongoDB Atlas: {e}")
    exit(1) 
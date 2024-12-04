from flask import Flask, jsonify
from flask_cors import CORS
from config.database import Database
from models import Port, ShippingLine, Rate
from routes.port_routes import port_routes
from routes.shipping_line_routes import shipping_line_routes
from routes.rate_routes import rate_routes
from routes.dashboard_routes import dashboard_routes
from routes.user_routes import user_routes
from routes.auth_routes import auth_routes
from routes.bulk_upload_routes import bulk_upload_routes
from middleware.error_handler import handle_error
from middleware.auth import auth_middleware
from datetime import datetime
import os

app = Flask(__name__)

# Configure CORS properly
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["https://goodrichlogisticsratecard.netlify.app", "http://localhost:3000"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }
     })

# Initialize database
db = Database.get_instance()

# Initialize models
port_model = Port(db.db)
shipping_line_model = ShippingLine(db.db)
rate_model = Rate(db.db)

# Make models available to routes
app.config['port_model'] = port_model
app.config['shipping_line_model'] = shipping_line_model
app.config['rate_model'] = rate_model

# Register blueprints
app.register_blueprint(auth_routes)
app.register_blueprint(port_routes)
app.register_blueprint(shipping_line_routes)
app.register_blueprint(rate_routes)
app.register_blueprint(user_routes)
app.register_blueprint(dashboard_routes)
app.register_blueprint(bulk_upload_routes)

# Register error handler
app.register_error_handler(Exception, handle_error)

# Register middleware
app.before_request(auth_middleware)

# Health check endpoints
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Test database connection
        db.db.command('ping')
        return jsonify({
            "status": "healthy",
            "message": "Backend is running and database is connected",
            "database": "connected",
            "version": "1.0.0"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "database": "disconnected"
        }), 500

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "message": "GLPL Rate API",
        "version": "1.0.0",
        "status": "running"
    })

# Test endpoint for frontend connection check
@app.route('/api/test', methods=['GET'])
def test_connection():
    try:
        # Test database connection
        db.db.command('ping')
        return jsonify({
            "status": "success",
            "message": "API is running and database is connected",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    # Get port from environment variable (Railway.app will set this)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 
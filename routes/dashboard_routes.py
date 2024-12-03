from flask import Blueprint, jsonify, request
from config.database import Database
from middleware.auth import require_auth
from datetime import datetime, timedelta
from services.activity_logger import activity_logger

dashboard_routes = Blueprint('dashboard_routes', __name__)
db = Database.get_instance().db

@dashboard_routes.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    try:
        stats = {
            'totalUsers': db.users.count_documents({}),
            'totalPorts': db.ports.count_documents({}),
            'totalShippingLines': db.shipping_lines.count_documents({}),
            'totalRates': db.rates.count_documents({})
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_routes.route('/api/dashboard/recent-activity', methods=['GET'])
@require_auth
def get_recent_activity():
    try:
        # Get recent activities from Redis
        activities = activity_logger.get_recent_activities(limit=20)
        
        # Format activities with descriptions
        formatted_activities = []
        for activity in activities:
            formatted_activity = {
                '_id': activity['_id'],
                'type': activity['type'],
                'timestamp': activity['timestamp'],
                'user': activity['user'],
                'description': activity_logger.format_activity_description(activity)
            }
            formatted_activities.append(formatted_activity)
            
        return jsonify(formatted_activities)
    except Exception as e:
        print(f"Error fetching recent activities: {str(e)}")
        return jsonify({"error": str(e)}), 500

@dashboard_routes.route('/api/dashboard/historical-activity', methods=['GET'])
@require_auth
def get_historical_activity():
    try:
        # Get query parameters
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 50))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Convert date strings to datetime if provided
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        
        # Get historical activities from MongoDB
        activities = activity_logger.get_historical_activities(
            skip=skip,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        # Format activities with descriptions
        formatted_activities = []
        for activity in activities:
            formatted_activity = {
                '_id': activity['_id'],
                'type': activity['type'],
                'timestamp': activity['timestamp'],
                'user': activity['user'],
                'description': activity_logger.format_activity_description(activity)
            }
            formatted_activities.append(formatted_activity)
            
        return jsonify(formatted_activities)
    except Exception as e:
        print(f"Error fetching historical activities: {str(e)}")
        return jsonify({"error": str(e)}), 500 
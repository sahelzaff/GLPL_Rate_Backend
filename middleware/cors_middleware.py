from flask import request, make_response

def cors_middleware():
    if request.method == 'OPTIONS':
        response = make_response()
        # Get the Origin header from the request
        origin = request.headers.get('Origin')
        allowed_origins = ['https://goodrichlogisticsratecard.netlify.app', 'http://localhost:3001']
        
        # Check if the request origin is in our allowed list
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
    return None
from flask import request, make_response

def cors_middleware():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin')
        allowed_origins = ['https://goodrichlogisticsratecard.netlify.app', 'http://localhost:3000']
        
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response
    return None
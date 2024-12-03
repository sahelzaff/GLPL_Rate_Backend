from flask import jsonify
import traceback

def handle_error(error):
    print(f"Error: {str(error)}")
    print(traceback.format_exc())
    
    response = {
        "error": str(error),
        "message": "An unexpected error occurred"
    }
    
    if hasattr(error, 'code'):
        return jsonify(response), error.code
    return jsonify(response), 500 
from golink.utils import is_valid_uuid, validate_token

from functools import wraps

from flask import (jsonify, request, current_app, session)


def token_required(f):
    """Login required function"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        """Token required decorator"""
        auth = request.headers.get('X-Auth-Token')
        if not auth:
            return jsonify({'error': 'Missing "X-Auth-Token" header'}), 401

        if not auth.startswith("Bearer "):
            return jsonify({'error': 'Invalid "X-Auth-Token" header: must start with "Bearer "'}), 401

        token = auth.split("Bearer ")[-1]
        user_data = validate_token(token, current_app.config)
        if not user_data['valid']:
            return jsonify({'error': user_data['error']}), 401

        session["user"] = user_data
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Login required function"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        """Login required decorator"""
        if 'user' in session:
            if session['user']['is_admin']:
                return f(*args, **kwargs)
            return jsonify({"error": True, "errorMessage": "Admin required"}), 401
        return jsonify({"error": True, "errorMessage": "Token required"}), 401

    return decorated_function


def is_valid_uid(f):
    """Login required function"""
    @wraps(f)
    def decorated_function(file_id, *args, **kwargs):
        """Token required decorator"""
        if not is_valid_uuid(file_id):
            return jsonify({}), 404
        return f(file_id, *args, **kwargs)

    return decorated_function

from datetime import datetime, timedelta

from flask import (Blueprint, current_app, jsonify, make_response, request)

from golink.utils import authenticate_user

import jwt

token = Blueprint('token', __name__, url_prefix='/')


@token.route('/api/token/create', methods=['POST'])
def create_token():

    if not request.json:
        return make_response(jsonify({'error': 'Missing body'}), 400)

    if not (request.json.get("username") and request.json.get("password")):
        return make_response(jsonify({'error': 'Missing either username or password in body'}), 400)

    # Only check ldap in prod
    if current_app.config['GOLINK_RUN_MODE'] == "prod":
        if not authenticate_user(request.json.get("username"), request.json.get("password"), current_app.config):
            return make_response(jsonify({'error': 'Incorrect credentials'}), 401)

    expire_date = datetime.utcnow() + timedelta(hours=current_app.config.get('TOKEN_DURATION'))
    token = jwt.encode({"username": request.json.get("username"), "exp": expire_date}, current_app.config['SECRET_KEY'], algorithm="HS256")
    return make_response(jsonify({'token': token}), 200)

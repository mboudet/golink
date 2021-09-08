import os

from email_validator import EmailNotValidError, validate_email

from flask import (Blueprint, current_app, jsonify, make_response, request, send_file)

from golink.db_models import PublishedFile
from golink.extensions import db
from golink.utils import get_celery_worker_status, is_valid_uuid, validate_token

from sqlalchemy import desc, func, or_


file = Blueprint('file', __name__, url_prefix='/')


@file.route('/api/status', methods=['GET'])
def status():
    mode = current_app.config.get("GOLINK_RUN_MODE")
    version = current_app.config.get("GOLINK_VERSION", "0.0.1")
    return make_response(jsonify({'version': version, 'mode': mode}), 200)


@file.route('/api/endpoints', methods=['GET'])
def endpoints():
    endpoints = {}
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        endpoints[rule.endpoint.split(".")[-1]] = rule.rule
    return jsonify(endpoints)


@file.route('/api/list', methods=['GET'])
def list_files():

    offset = request.args.get('offset', 0)

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    limit = request.args.get('limit', 10)

    try:
        limit = int(limit)
    except ValueError:
        limit = 0

    files = PublishedFile().query.order_by(desc(PublishedFile.publishing_date))
    total = files.count()
    files = files.limit(limit).offset(offset)
    data = []

    for file in files:
        data.append({
            'uri': file.id,
            'file_name': file.file_name,
            'size': file.size,
            'status': file.status,
            'downloads': file.downloads,
            'publishing_date': file.publishing_date.strftime('%Y-%m-%d')
        })

    return make_response(jsonify({'files': data, 'total': total}), 200)


@file.route('/api/view/<file_id>', methods=['GET'])
def view_file(file_id):
    if not is_valid_uuid(file_id):
        return make_response(jsonify({}), 404)

    datafile = PublishedFile().query.get(file_id)

    if not datafile:
        return make_response(jsonify({}), 404)

    repo = current_app.repos.get_repo(datafile.repo_path)
    path = datafile.file_path
    current_app.logger.info("API call: Getting file %s" % file_id)
    if os.path.exists(path):
        # We don't know the status of Baricadr, so, check the size for completion
        if datafile.status == "pulling" and os.path.getsize(path) == datafile.size:
            datafile.status = "available"
            db.session.commit()
        # Should not happen: for testing/dev purposes
        if datafile.status == "unavailable":
            datafile.status = "available"
            db.session.commit()
    elif datafile.status == "available":
        if repo.has_baricadr:
            # TODO : Add baricadr check if the file exists
            datafile.status = "pullable"
        else:
            datafile.status = "unavailable"
        db.session.commit()

    data = {
        "file": {
            "contact": datafile.contact,
            "owner": datafile.owner,
            "status": datafile.status,
            "file_name": datafile.file_name,
            "path": datafile.file_path,
            "size": datafile.size,
            "hash": datafile.hash,
            "publishing_date": datafile.publishing_date.strftime('%Y-%m-%d')
        }
    }

    return make_response(jsonify(data), 200)


@file.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    if not is_valid_uuid(file_id):
        return make_response(jsonify({}), 404)
    current_app.logger.info("API call: Download file %s" % file_id)
    datafile = PublishedFile().query.get(file_id)

    if not datafile:
        return make_response(jsonify({}), 404)

    path = datafile.file_path

    if datafile.status == "unpublished":
        return make_response(jsonify({}), 404)

    if os.path.exists(path):
        datafile.downloads = datafile.downloads + 1
        db.session.commit()
        res = send_file(path, as_attachment=True)

        if current_app.config.get("USE_X_SENDFILE"):
            res.headers['X-Accel-Redirect'] = path
            res.headers['X-Accel-Buffering'] = "no"
        return res
    else:
        return make_response(jsonify({'error': 'Missing file'}), 404)


@file.route('/api/pull/<file_id>', methods=['POST'])
def pull_file(file_id):
    if not is_valid_uuid(file_id):
        return make_response(jsonify({}), 404)
    current_app.logger.info("API call: Getting file %s" % file_id)
    datafile = PublishedFile().query.get_or_404(file_id)

    email = None
    if 'email' in request.json and request.json['email']:
        email = request.json['email']
        try:
            v = validate_email(email)
            email = v["email"]
        except EmailNotValidError as e:
            return jsonify({'error': str(e)}), 400

    repo = current_app.repos.get_repo(datafile.repo_path)
    path = datafile.file_path

    if os.path.exists(path):
        return make_response(jsonify({'message': 'File already available'}), 200)
    else:
        if repo.has_baricadr:
            current_app.celery.send_task("pull", (datafile.id, email))
            return make_response(jsonify({'message': 'Ok'}), 200)
        else:
            return make_response(jsonify({'message': 'Not managed by Baricadr'}), 400)


@file.route('/api/publish', methods=['POST'])
def publish_file():
    # Auth stuff
    auth = request.headers.get('X-Auth-Token')
    if not auth:
        return make_response(jsonify({'error': 'Missing "X-Auth-Token" header'}), 401)

    if not auth.startswith("Bearer "):
        return make_response(jsonify({'error': 'Invalid "X-Auth-Token" header: must start with "Bearer "'}), 401)

    token = auth.split("Bearer ")[-1]
    user_data = validate_token(token, current_app.config)
    if not user_data['valid']:
        return make_response(jsonify({'error': user_data['error']}), 401)

    if not request.json:
        return make_response(jsonify({'error': 'Missing body'}), 400)

    if 'path' not in request.json:
        return make_response(jsonify({'error': 'Missing path'}), 400)

    if not os.path.exists(request.json['path']):
        return make_response(jsonify({'error': 'File not found at path %s' % request.json['path']}), 400)

    if os.path.isdir(request.json['path']):
        return make_response(jsonify({'error': 'Path must not be a folder'}), 400)

    repo = current_app.repos.get_repo(request.json['path'])
    if not repo:
        return make_response(jsonify({'error': 'File %s is not in any publishable repository' % request.json['path']}), 400)

    checks = repo.check_publish_file(request.json['path'], user_data=user_data)

    if checks["error"]:
        return make_response(jsonify({'error': 'Error checking file : %s' % checks["error"]}), 400)

    celery_status = get_celery_worker_status(current_app.celery)
    if celery_status['availability'] is None:
        current_app.logger.error("Received publish request on path '%s', but no Celery worker available to process the request. Aborting." % request.json['path'])
        return jsonify({'error': 'No Celery worker available to process the request'}), 400

    email = None
    if 'email' in request.json and request.json['email']:
        email = request.json['email']
        try:
            v = validate_email(email)
            email = [v["email"]]
        except EmailNotValidError as e:
            return make_response(jsonify({'error': str(e)}), 400)

    contact = None
    if 'contact' in request.json and request.json['contact']:
        contact = request.json['contact']
        try:
            v = validate_email(contact)
            contact = v["email"]
        except EmailNotValidError as e:
            return make_response(jsonify({'error': str(e)}), 400)

    file_id = repo.publish_file(request.json['path'], user_data, email=email, contact=contact)

    res = "File registering. An email will be sent to you when the file is ready." if email else "File registering. It should be ready soon"

    return make_response(jsonify({'message': res, 'file_id': file_id}), 200)


@file.route('/api/unpublish/<file_id>', methods=['DELETE'])
def unpublish_file(file_id):

    if not is_valid_uuid(file_id):
        return make_response(jsonify({}), 404)
    datafile = PublishedFile().query.get_or_404(file_id)

    auth = request.headers.get('X-Auth-Token')
    if not auth:
        return make_response(jsonify({'error': 'Missing "X-Auth-Token" header'}), 401)

    if not auth.startswith("Bearer "):
        return make_response(jsonify({'error': 'Invalid "X-Auth-Token" header: must start with "Bearer "'}), 401)

    token = auth.split("Bearer ")[-1]
    user_data = validate_token(token, current_app.config)
    if not user_data['valid']:
        return make_response(jsonify({'error': user_data['error']}), 401)

    if not (datafile.owner == user_data["username"] or user_data["is_admin"]):
        return make_response(jsonify({}), 401)

    datafile.status = "unpublished"
    db.session.commit()

    return make_response(jsonify({'message': 'File unpublished'}), 200)


@file.route('/api/search', methods=['GET'])
def search():

    offset = request.args.get('offset', 0)

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    limit = request.args.get('limit', 10)

    try:
        limit = int(limit)
    except ValueError:
        limit = 0

    file_name = request.args.get("file")
    if not file_name:
        return make_response(jsonify({'data': []}), 200)

    if is_valid_uuid(file_name):
        files = PublishedFile().query.order_by(desc(PublishedFile.publishing_date)).filter(PublishedFile.id == file_name, PublishedFile.status != "unpublished")
    else:
        files = PublishedFile().query.order_by(desc(PublishedFile.publishing_date)).filter(or_(func.lower(PublishedFile.file_name).contains(file_name.lower())), PublishedFile.status != "unpublished")

    total = files.count()

    files = files.limit(limit).offset(offset)

    data = []

    for file in files:
        data.append({
            'uri': file.id,
            'file_name': file.file_name,
            'size': file.size,
            'status': file.status,
            'downloads': file.downloads,
            "publishing_date": file.publishing_date.strftime('%Y-%m-%d')
        })

    return make_response(jsonify({'files': data, 'total': total}), 200)

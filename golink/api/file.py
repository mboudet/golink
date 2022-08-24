import os

from collections import defaultdict

from email_validator import EmailNotValidError, validate_email

from flask import (Blueprint, current_app, jsonify, make_response, request, session, send_file)

from golink.db_models import PublishedFile, Tag
from golink.extensions import db
from golink.utils import get_celery_worker_status, is_valid_uuid, get_or_create

from golink.decorators import token_required, admin_required, is_valid_uid

from sqlalchemy import desc, func


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

    tags = request.args.getlist("tags") or request.args.getlist("tags[]")
    tags = [t.strip().lower() for t in tags]

    tag_list = []

    if tags:
        tag_list = Tag.query.filter(Tag.tag.in_(tags)).all()

    files = PublishedFile().query.filter(*[PublishedFile.tags.contains(t) for t in tag_list], PublishedFile.status != "unpublished").order_by(desc(PublishedFile.publishing_date))
    total = files.count()
    files = files.limit(limit).offset(offset)
    data = []

    tags_dict = defaultdict(lambda: 0)

    for file in files:
        file_tag_list = []
        for tag in file.tags:
            file_tag_list.append(tag.tag)
            tags_dict[tag.tag] += 1

        data.append({
            'uri': file.id,
            'file_name': file.file_name,
            'size': file.size,
            'version': file.version,
            'status': file.status,
            'downloads': file.downloads,
            'publishing_date': file.publishing_date.strftime('%Y-%m-%d'),
            'tags': file_tag_list
        })

    all_tags_list = [{"tag": key, "count": count} for key, count in tags_dict.items()]

    return make_response(jsonify({'files': data, 'total': total, 'tags': all_tags_list}), 200)


@file.route('/api/tag/add/<file_id>', methods=['PUT'])
@token_required
@is_valid_uid
def tag_file(file_id):

    if not request.get_json(silent=True):
        return make_response(jsonify({'error': 'Missing body'}), 400)

    tags = request.json.get('tags', [])

    if tags:
        if not isinstance(tags, list):
            if isinstance(tags, str):
                tags = [tags]
            else:
                return make_response(jsonify({'error': 'tags is neither a list nor a string'}), 400)
    else:
        return make_response(jsonify({"error": "Missing tags"}), 400)

    tags = [t.strip().lower() for t in tags]

    datafile = PublishedFile().query.get_or_404(file_id)

    if not (datafile.owner == session['user']["username"] or session['user']["is_admin"]):
        return make_response(jsonify({}), 401)

    missing_tags = set(tags) - set([tag.tag for tag in datafile.tags])
    if missing_tags:
        tag_entities = [get_or_create(db.session, Tag, tag=tag) for tag in missing_tags]
        db.session.commit()
        for tag in tag_entities:
            datafile.tags.append(tag)
        db.session.commit()

    data = {
        "file": {
            "contact": datafile.contact,
            "owner": datafile.owner,
            "status": datafile.status,
            "file_name": datafile.file_name,
            "version": datafile.version,
            "size": datafile.size,
            "hash": datafile.hash,
            "publishing_date": datafile.publishing_date.strftime('%Y-%m-%d'),
            'tags': [tag.tag for tag in datafile.tags]
        }
    }

    return make_response(jsonify(data), 200)


@file.route('/api/tag/remove/<file_id>', methods=['PUT'])
@token_required
@is_valid_uid
def untag_file(file_id):

    if not request.get_json(silent=True):
        return make_response(jsonify({'error': 'Missing body'}), 400)

    tags = request.json.get('tags', [])

    if tags:
        if not isinstance(tags, list):
            if isinstance(tags, str):
                tags = [tags]
            else:
                return make_response(jsonify({'error': 'tags is neither a list nor a string'}), 400)
    else:
        return make_response(jsonify({"error": "Missing tags"}), 400)

    datafile = PublishedFile().query.get_or_404(file_id)

    if not (datafile.owner == session['user']["username"] or session['user']["is_admin"]):
        return make_response(jsonify({}), 401)

    tags_to_remove = set(tags).intersection(set([tag.tag for tag in datafile.tags]))

    for tag in datafile.tags:
        if tag.tag in tags_to_remove:
            if len(tag.files) == 1:
                db.session.delete(tag)
            else:
                datafile.tags.remove(tag)

    db.session.commit()

    data = {
        "file": {
            "contact": datafile.contact,
            "owner": datafile.owner,
            "status": datafile.status,
            "file_name": datafile.file_name,
            "version": datafile.version,
            "size": datafile.size,
            "hash": datafile.hash,
            "publishing_date": datafile.publishing_date.strftime('%Y-%m-%d'),
            'tags': [tag.tag for tag in datafile.tags]
        }
    }

    return make_response(jsonify(data), 200)


@file.route('/api/view/<file_id>', methods=['GET'])
@is_valid_uid
def view_file(file_id):
    datafile = PublishedFile().query.get_or_404(file_id)

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

    # TODO : How do we check the baricadr process? Store the task ID?

    siblings = []

    if datafile.version_of:
        main_file = datafile.version_of
        siblings.append({"uri": main_file.id, "version": main_file.version, "status": main_file.status, "publishing_date": main_file.publishing_date.strftime('%Y-%m-%d')})
        for file in datafile.version_of.subversions:
            if not file.id == datafile.id:
                siblings.append({"uri": file.id, "version": file.version, "status": file.status, "publishing_date": file.publishing_date.strftime('%Y-%m-%d')})
    elif datafile.subversions:
        for file in datafile.subversions:
            if not file.id == datafile.id:
                siblings.append({"uri": file.id, "version": file.version, "status": file.status, "publishing_date": file.publishing_date.strftime('%Y-%m-%d')})

    data = {
        "file": {
            "contact": datafile.contact,
            "owner": datafile.owner,
            "status": datafile.status,
            "path": datafile.file_path,
            "file_name": datafile.file_name,
            "version": datafile.version,
            "size": datafile.size,
            "hash": datafile.hash,
            "publishing_date": datafile.publishing_date.strftime('%Y-%m-%d'),
            "siblings": siblings,
            'tags': [tag.tag for tag in datafile.tags]
        }
    }

    return make_response(jsonify(data), 200)


@file.route('/api/download/<file_id>', methods=['GET'])
@is_valid_uid
def download_file(file_id):
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
@is_valid_uid
def pull_file(file_id):
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
@token_required
def publish_file():

    if not request.get_json(silent=True):
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

    tags = request.json.get('tags', [])

    if tags:
        if not isinstance(tags, list):
            if isinstance(tags, str):
                tags = [tags]
            else:
                return make_response(jsonify({'error': 'tags is neither a list nor a string'}), 400)
    tags = [t.strip().lower() for t in tags]
    tags = set(tags)
    version = 1

    linked_to = request.json.get('linked_to')
    linked_datafile = None
    inherit_tags = request.json.get('inherit_tags', True)
    if linked_to:
        if not is_valid_uuid(linked_to):
            return make_response(jsonify({'error': 'linked_to %s is not a valid id' % request.json['linked_to']}), 400)
        linked_datafile = PublishedFile().query.get(linked_to)

        if not linked_datafile:
            return make_response(jsonify({'error': 'linked_to %s file does not exists' % request.json['linked_to']}), 404)

        # Check linnked datafile is in same repo
        if not linked_datafile.repo_path == repo.local_path:
            return make_response(jsonify({'error': 'linked_to %s file is not in the same repository' % request.json['linked_to']}), 404)

        # Silently redirect to original file. Maybe it would be better to throw an error?
        if linked_datafile.version_of:
            linked_datafile = linked_datafile.version_of

        if inherit_tags:
            tags |= set([tag.tag for tag in linked_datafile.tags])

        version = len(linked_datafile.subversions) + 2

    checks = repo.check_publish_file(request.json['path'], user_data=session['user'])

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

    file_id = repo.publish_file(request.json['path'], session['user'], version=version, email=email, contact=contact, linked_to=linked_datafile, tags=tags)

    res = "File registering. An email will be sent to you when the file is ready." if email else "File registering. It should be ready soon"

    return make_response(jsonify({'message': res, 'file_id': file_id, 'version': version}), 200)


@file.route('/api/unpublish/<file_id>', methods=['DELETE'])
@is_valid_uid
@token_required
def unpublish_file(file_id):
    datafile = PublishedFile().query.get_or_404(file_id)

    if not (datafile.owner == session['user']["username"] or session['user']["is_admin"]):
        return make_response(jsonify({}), 401)

    datafile.status = "unpublished"
    db.session.commit()
    return make_response(jsonify({'message': 'File unpublished'}), 200)


@file.route('/api/delete/<file_id>', methods=['DELETE'])
@token_required
@admin_required
@is_valid_uid
def delete_file(file_id):
    datafile = PublishedFile().query.get_or_404(file_id)

    db.session.delete(datafile)
    db.session.commit()

    return make_response(jsonify({'message': 'File deleted'}), 200)


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

    file_name = request.args.get("file", "")
    tags = request.args.getlist("tags") or request.args.getlist("tags[]")

    tags = [t.strip().lower() for t in tags]

    tag_list = []

    if tags:
        tag_list = Tag.query.filter(Tag.tag.in_(tags)).all()

    if not (file_name or tag_list):
        return make_response(jsonify({'files': [], 'total': 0}), 200)

    if file_name and is_valid_uuid(file_name):
        files = PublishedFile().query.order_by(desc(PublishedFile.publishing_date)).filter(*[PublishedFile.tags.contains(t) for t in tag_list], PublishedFile.id != file_name, PublishedFile.status != "unpublished")
    else:
        files = PublishedFile().query.order_by(desc(PublishedFile.publishing_date)).filter(*[PublishedFile.tags.contains(t) for t in tag_list], func.lower(PublishedFile.file_name).contains(file_name.lower()), PublishedFile.status != "unpublished")

    total = files.count()

    files = files.limit(limit).offset(offset)

    data = []

    tags_dict = defaultdict(lambda: 0)

    for file in files:
        file_tag_list = []
        for tag in file.tags:
            file_tag_list.append(tag.tag)
            tags_dict[tag.tag] += 1

    for file in files:
        data.append({
            'uri': file.id,
            'file_name': file.file_name,
            'size': file.size,
            'version': file.version,
            'status': file.status,
            'downloads': file.downloads,
            "publishing_date": file.publishing_date.strftime('%Y-%m-%d'),
            'tags': file_tag_list
        })

    all_tags_list = [{"tag": key, "count": count} for key, count in tags_dict.items()]

    return make_response(jsonify({'files': data, 'total': total, 'tags': all_tags_list}), 200)

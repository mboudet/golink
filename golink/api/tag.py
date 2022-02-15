from flask import (Blueprint, jsonify, make_response)

from golink.db_models import Tag

tag = Blueprint('tag', __name__, url_prefix='/')


@tag.route('/api/tag/list', methods=['GET'])
def list_tags():
    tag_list = [{"tag": tag.tag, "count": len(tag.files)} for tag in Tag.query.all()]

    return make_response(jsonify({'tags': tag_list}), 200)

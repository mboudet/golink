from uuid import UUID

import jwt

from ldap3 import Connection, NONE, Server


def get_celery_worker_status(app):
    i = app.control.inspect()
    availability = i.ping()
    # stats = i.stats()
    result = {
        'availability': availability,
        # 'stats': stats,
    }
    return result


def get_celery_tasks(app):
    i = app.control.inspect()
    active_tasks = _get_celery_task_ids(i.active())
    reserved_tasks = _get_celery_task_ids(i.reserved())
    scheduled_tasks = _get_celery_task_ids(i.scheduled())
    result = {
        'active_tasks': active_tasks,
        'reserved_tasks': reserved_tasks,
        'scheduled_tasks': scheduled_tasks
    }
    return result


def _get_celery_task_ids(full_dict):
    res = []
    for worker in full_dict:
        for task in full_dict[worker]:
            res.append(task['id'])

    return res


def celery_task_is_in_queue(celery, task_id):

    cel_tasks = get_celery_tasks(celery)

    return task_id in cel_tasks['active_tasks'] \
        or task_id in cel_tasks['reserved_tasks'] \
        or task_id in cel_tasks['scheduled_tasks']


# Borrowed from https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def authenticate_user(username, password, config):
    server = Server(config.get("LDAP_HOST"), config.get("LDAP_PORT", 389), get_info=NONE)
    conn = Connection(server, auto_bind=True)
    user = conn.search(config.get("LDAP_BASE_QUERY"), '(uid=%s)' % username, attributes=['uidNumber'], size_limit=1, time_limit=10)
    if not user:
        return False
    full_dn = conn.entries[0].entry_dn
    # Check password
    logged_in = conn.rebind(user=full_dn, password=password)
    conn.unbind()
    return logged_in


def validate_token(token, config):
    try:
        payload = jwt.decode(token, config['SECRET_KEY'], algorithms=["HS256"])
    except jwt.exceptions.ExpiredSignatureError:
        return {"valid": False, "error": "Expired token"}
    except jwt.exceptions.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}
    return {"valid": True, "username": payload['username'], "is_admin": payload['username'] in config.get('ADMIN_USERS')}


def get_user_ldap_data(username, config):
    data = {"user_id": None, "user_group_names": [], "user_group_ids": [], "error": None}
    server = Server(config.get("LDAP_HOST"), config.get("LDAP_PORT", 389), get_info=NONE)
    conn = Connection(server, auto_bind=True)
    # Basic query to see if it works
    user = conn.search(config.get("LDAP_BASE_QUERY"), '(uid=%s)' % username, attributes=['uidNumber'], size_limit=1, time_limit=10)
    if not user:
        data['error'] = "Could not find user %s in LDAP" % username
        return data
    data['user_id'] = conn.entries[0]['uidNumber'].values[0]
    conn.search(config.get("LDAP_BASE_QUERY"), '(memberuid=%s)' % username, attributes=['gidNumber', 'cn'], time_limit=10)
    for group in conn.entries:
        data['user_group_names'].append(group['cn'][0])
        data['user_group_ids'].append(group['gidNumber'][0])

    conn.unbind()
    return data


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance

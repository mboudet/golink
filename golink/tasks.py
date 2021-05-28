import hashlib
import os
import time

from celery.signals import task_postrun

from flask_mail import Message

from golink.app import create_app, create_celery
from golink.db_models import PublishedFile
from golink.extensions import db
from golink.extensions import mail

import requests


app = create_app(config='../local.cfg', is_worker=True)
app.app_context().push()
celery = create_celery(app)


def on_failure(self, exc, task_id, args, kwargs, einfo):

    app.logger.warning("Task %s failed. Exception raised: %s" % (task_id, str(exc)))
    p_file = PublishedFile.query.filter_by(id=args[0]).one()
    p_file.error = str(exc)

    # args[2] is the email address
    if args[2]:
        body = """Hello,
Your publishing request on file '{path}' failed, with the following error:
{error}
Contact the administrator for more info.
Cheers
"""
        msg = Message(subject="Golink: Publishing task on {path} failed".format(path=args[1]),
                      body=body.format(path=args[1], error=str(exc)),
                      sender=app.config.get('MAIL_SENDER', 'from@example.com'),
                      recipients=args[2])
        mail.send(msg)

    p_file.status = 'failed'
    db.session.commit()


@celery.task(bind=True, name="publish", on_failure=on_failure)
def publish_file(self, file_id, old_path, email=""):
    # Send task to copy file
    # (Copy file, create symlink)

    # Wait a bit in case the tasks begin just before it is recorded in the db
    time.sleep(2)
    p_file = PublishedFile.query.filter_by(id=file_id).one()
    p_file.task_id = self.request.id
    p_file.status = 'starting'
    db.session.commit()
    # Copy or move?

    file_md5 = md5(p_file.file_path)
    p_file.hash = file_md5
    p_file.status = 'available'
    db.session.commit()

    if email:
        body = """Hello,
Your publishing request on file '{path}' succeded.
Your file should be available here : {file_url}
Cheers
"""
        msg = Message(subject="Golink: Publishing task on {path} succeded".format(path=old_path),
                      body=body.format(path=old_path, file_url="%s/data/%s" % (app.config.get("BASE_URL"), p_file.id)),
                      sender=app.config.get('MAIL_SENDER', 'from@example.com'),
                      recipients=email)
        mail.send(msg)


@celery.task(bind=True, name="pull")
def pull_file(self, file_id, email=""):
    # Task to pull file from baricadr
    p_file = PublishedFile.query.filter_by(id=file_id).one()
    repo = app.repos.get_repo(p_file.repo_path)
    path = os.path.join(repo.public_folder, p_file.stored_file_name)
    pull_from_baricadr(path, email=email)


@task_postrun.connect
def close_session(*args, **kwargs):
    # Flask SQLAlchemy will automatically create new sessions for you from
    # a scoped session factory, given that we are maintaining the same app
    # context, this ensures tasks have a fresh session (e.g. session errors
    # won't propagate across tasks)
    db.session.remove()


def pull_from_baricadr(file_path, email=""):
    url = "%s/pull" % app.config.get("BARICADR_URL")
    data = {"path": file_path}
    if email:
        data['email'] = email
    requests.post(url, auth=(app.config.get("BARICADR_USER"), app.config.get("BARICADR_PASSWORD")), json=data)
    # How do we manage failure? Mail admin?


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

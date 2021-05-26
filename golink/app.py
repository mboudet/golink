import os
import grp
import pwd

from celery import Celery

from flask import Flask, g

from golink.api.file import file
from golink.api.token import token
from golink.api.view import view

from ldap3 import Connection, NONE, Server

import requests

# Import model classes for flaks migrate
from .db_models import PublishedFile  # noqa: F401
from .extensions import (celery, db, mail, migrate)
from .middleware import PrefixMiddleware
from .model.repos import Repos


__all__ = ('create_app', 'create_celery', )

BLUEPRINTS = (
    file,
    token,
    view
)

CONFIG_KEYS = (
    'SECRET_KEY',
    'GOLINK_REPOS_CONF',
    'MAIL_SENDER',
    'MAIL_ADMIN',
    'BASE_URL',
    'TASK_LOG_DIR',
    'DEBUG',
    'TESTING',
    'BROKER_TRANSPORT',
    'CELERY_BROKER_URL',
    'CELERY_RESULT_BACKEND',
    'CELERY_TASK_SERIALIZER',
    'CELERY_DISABLE_RATE_LIMITS',
    'CELERY_ACCEPT_CONTENT',
    'SQLALCHEMY_DATABASE_URI',
    'SQLALCHEMY_ECHO',
    'SQLALCHEMY_TRACK_MODIFICATIONS',
    'MAIL_SERVER',
    'MAIL_PORT',
    'MAIL_USE_SSL',
    'MAIL_SENDER',
    'MAIL_SUPPRESS_SEND',
    'LOG_FOLDER',
    'USE_BARICADR',
    'BARICADR_URL',
    'BARICADR_USER',
    'BARICADR_PASSWORD',
    'LDAP_HOST',
    'LDAP_PORT',
    'LDAP_BASE_QUERY',
    'TOKEN_DURATION',
    'ADMIN_USERS',
    'PROXY_PREFIX'
)


def create_app(config=None, app_name='golink', blueprints=None, run_mode=None, is_worker=False):
    app = Flask(app_name,
                static_folder='static',
                template_folder="templates"
                )

    with app.app_context():

        # Can be used to check if some code is executed in a Celery worker, or in the web app
        app.is_worker = is_worker

        configs = {
            "dev": "golink.config.DevelopmentConfig",
            "test": "golink.config.TestingConfig",
            "prod": "golink.config.ProdConfig"
        }
        if run_mode:
            config_mode = run_mode
        else:
            config_mode = os.getenv('GOLINK_RUN_MODE', 'prod')

        if 'GOLINK_RUN_MODE' not in app.config:
            app.config['GOLINK_RUN_MODE'] = config_mode

        app.config.from_object(configs[config_mode])

        app.config.from_pyfile('../local.cfg', silent=True)
        if config:
            app.config.from_pyfile(config)

        app.config = _merge_conf_with_env_vars(app.config)

        if not app.config.get("SECRET_KEY"):
            raise Exception("Missing secret_key")

        token_duration = app.config.get("TOKEN_DURATION", 6)
        try:
            token_duration = int(token_duration)
        except ValueError:
            raise ValueError("Malformed configuration for TOKEN_DURATION : must be a positive integer")

        if token_duration < 1:
            raise ValueError("Malformed configuration for TOKEN_DURATION : must be a positive integer")

        app.config["TOKEN_DURATION"] = token_duration

        admin_users = app.config.get("ADMIN_USERS", [])
        if not type(admin_users) == list:
            raise ValueError("ADMIN_USERS variable is not a list")

        app.config["ADMIN_USERS"] = admin_users

        if 'TASK_LOG_DIR' in app.config:
            app.config['TASK_LOG_DIR'] = os.path.abspath(app.config['TASK_LOG_DIR'])
        else:
            app.config['TASK_LOG_DIR'] = os.path.abspath(os.getenv('TASK_LOG_DIR', '/var/log/golink/tasks/'))

        if app.is_worker:
            os.makedirs(app.config['TASK_LOG_DIR'], exist_ok=True)

        if app.config.get("PROXY_PREFIX"):
            app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=app.config.get("PROXY_PREFIX").rstrip("/"))

        if config_mode == "prod":
            # Check ldap
            if not app.config.get("LDAP_HOST"):
                raise Exception("Missing LDAP_HOST in conf")
            if not app.config.get("LDAP_BASE_QUERY"):
                raise Exception("Missing LDAP_BASE_QUERY in conf")
            if not check_ldap(app.config):
                raise Exception("Could not connect to the LDAP")

        app.baricadr_enabled = False
        if app.config.get('USE_BARICADR') is True:
            # TODO : Print error somewhere...
            if check_baricadr(app.config):
                app.baricadr_enabled = True

        # Load the list of golink repositories
        if 'GOLINK_REPOS_CONF' in app.config:
            repos_file = app.config['GOLINK_REPOS_CONF']
        else:
            repos_file = os.getenv('GOLINK_REPOS_CONF', '/etc/golink/repos.yml')
        app.repos = Repos(repos_file)

        if blueprints is None:
            blueprints = BLUEPRINTS

        blueprints_fabrics(app, blueprints)
        extensions_fabrics(app)
        configure_logging(app)

        gvars(app)

    return app


def create_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask

    app.celery = celery
    return celery


def blueprints_fabrics(app, blueprints):
    """Configure blueprints in views."""

    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def extensions_fabrics(app):
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    celery.config_from_object(app.config)


def gvars(app):
    @app.before_request
    def gdebug():
        if app.debug:
            g.debug = True
        else:
            g.debug = False


def configure_logging(app):
    """Configure file(info) and email(error) logging."""

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return

    import logging
    from logging.handlers import SMTPHandler

    # Set log level
    if app.config['GOLINK_RUN_MODE'] == 'test':
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    info_log = os.path.join(app.config['LOG_FOLDER'], 'info.log')

    if not os.path.exists(app.config['LOG_FOLDER']):
        os.makedirs(app.config['LOG_FOLDER'])

    # Ensure log file is writable by nginx (worker)
    if not app.is_worker:
        if not os.path.exists(info_log):
            with open(info_log, 'w') as fp:
                pass
        os.chown(info_log, pwd.getpwnam("nginx").pw_uid, grp.getgrnam("nginx").gr_gid)

    info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)

    credentials = None
    if app.config.get("MAIL_PASSWORD"):
        credentials = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    mailhost = app.config['MAIL_SERVER']
    if 'MAIL_PORT' in app.config:
        mailhost = (app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
    mail_handler = SMTPHandler(mailhost,
                               app.config['MAIL_SENDER'],
                               app.config['MAIL_ADMIN'],
                               'GOLINK failed!',
                               credentials)
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(mail_handler)


def _merge_conf_with_env_vars(config):

    for key in CONFIG_KEYS:
        envval = os.getenv(key)
        if envval is not None:
            config[key] = envval

    return config


def check_baricadr(config):
    baricadr_enabled = False
    if (config.get("BARICADR_URL") and config.get("BARICADR_USER") and config.get("BARICADR_PASSWORD")):
        url = "%s/version" % config.get("BARICADR_URL")
        res = requests.get(url, auth=(config.get("BARICADR_USER"), config.get("BARICADR_PASSWORD")))
        # TODO : Maybe restrict compatible versions here?
        if res.status_code == 200 and "version" in res.json:
            baricadr_enabled = True
    return baricadr_enabled


def check_ldap(config):
    server = Server(config.get("LDAP_HOST"), config.get("LDAP_PORT", 389), get_info=NONE)
    conn = Connection(server, auto_bind=True)
    # Basic query to see if it works
    has_ldap = conn.bind()
    conn.unbind()
    return has_ldap

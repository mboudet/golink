from celery import Celery

from flask_mail import Mail

from flask_migrate import Migrate

from flask_sqlalchemy import SQLAlchemy
from .base import metadata

mail = Mail()
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
celery = Celery()

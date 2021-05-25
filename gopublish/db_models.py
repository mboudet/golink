import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from .extensions import db


class PublishedFile(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    task_id = db.Column(db.String(255), index=True)
    # Maybe store it as text? Or encoded?
    file_name = db.Column(db.String(255), index=True, nullable=False)
    stored_file_name = db.Column(db.String(255), index=True, nullable=False)
    version = db.Column(db.Integer, index=True, default=1, nullable=False)
    # To check quickly if managed by baricadr
    repo_path = db.Column(db.String(255), index=True, nullable=False)
    hash = db.Column(db.String(255), index=True, default='Computing..')
    status = db.Column(db.String(255), nullable=False, default='creating')
    publishing_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    # Maybe store it as a string? We don't need to run queries on size
    size = db.Column(db.BigInteger, index=True, default=0, nullable=False)
    owner = db.Column(db.String(255), index=True, nullable=False)
    contact = db.Column(db.String(255), index=True)
    downloads = db.Column(db.Integer, index=True, default=0)
    error = db.Column(db.Text())

    def __repr__(self):
        return '<PublishedFile {}>'.format(self.id)

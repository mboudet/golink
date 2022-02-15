import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import Table
from .base import Base

from .extensions import db

junction_table = Table(
    "file_tag",
    Base.metadata,
    db.Column("file_id", db.ForeignKey('published_file.id'), primary_key=True),
    db.Column("tag_id", db.ForeignKey('tag.id'), primary_key=True)
)


class PublishedFile(db.Model):
    __tablename__ = 'published_file'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    task_id = db.Column(db.String(255), index=True)
    # Maybe store it as text? Or encoded?
    file_name = db.Column(db.String(255), index=True, nullable=False)
    file_path = db.Column(db.String(255), index=True, nullable=False)
    version = db.Column(db.Integer, index=True, default=1, nullable=False)
    version_of_id = db.Column(UUID(as_uuid=True), db.ForeignKey('published_file.id'))  # parent company ID
    version_of = db.relationship('PublishedFile', remote_side='PublishedFile.id', backref=db.backref('subversions'))
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
    tags = db.relationship("Tag", secondary=junction_table, backref="files")

    def __repr__(self):
        return '<PublishedFile {}>'.format(self.id)


class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    tag = db.Column(db.String(255), index=True)

    def __repr__(self):
        return self.tag

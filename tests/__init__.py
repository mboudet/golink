import hashlib
import os
from datetime import datetime, timedelta

from golink.db_models import PublishedFile
from golink.extensions import db

import jwt


class GolinkTestCase():

    def create_mock_published_file(self, client, status):
        file_name = "my_file_to_publish.txt"
        public_file = "/repos/myrepo/my_file_to_publish.txt"
        size = os.path.getsize(public_file)
        hash = self.md5(public_file)
        size = os.path.getsize(public_file)
        pf = PublishedFile(file_name=file_name, file_path=public_file, repo_path="/repos/myrepo", size=size, hash=hash, status=status, owner="root")
        db.session.add(pf)
        db.session.commit()
        return str(pf.id)

    def create_mock_token(self, app, expire_now=False):
        if expire_now:
            expire_at = datetime.utcnow() - timedelta(hours=12)
        else:
            expire_at = datetime.utcnow() + timedelta(hours=12)

        token = jwt.encode({"username": "root", "exp": expire_at}, app.config['SECRET_KEY'], algorithm="HS256")
        return token

    def md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

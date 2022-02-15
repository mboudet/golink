import os

from flask import current_app

from golink.db_models import PublishedFile, Tag
from golink.extensions import db
from golink.utils import get_user_ldap_data

import yaml


class Repo():

    def __init__(self, local_path, conf):

        self.local_path = local_path  # No trailing slash
        self.conf = conf

        self.has_baricadr = False
        if current_app.baricadr_enabled and 'has_baricadr' in conf and conf['has_baricadr'] is True:
            self.has_baricadr = True

        self.allowed_groups = conf.get("allowed_groups", [])
        if not type(self.allowed_groups) == list:
            raise ValueError("allowed_groups for path '%s' is not a list" % local_path)

        self.allowed_users = conf.get("allowed_users", [])
        if not type(self.allowed_users) == list:
            raise ValueError("allowed_users for path '%s' is not a list" % local_path)

    def is_in_repo(self, path):
        path = os.path.join(path, "")
        return path.startswith(os.path.join(self.local_path, ""))

    def check_publish_file(self, file_path, user_data):
        username = user_data["username"]
        is_admin = user_data["is_admin"]

        if not os.path.exists(file_path):
            return {"available": False, "error": "Target file %s does not exists" % file_path}

        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)

        # Check is user is in allowed groups
        # Check if user is in allowed users
        # If no allowed groups and no allowed_users: check if is owner

        if current_app.config['GOLINK_RUN_MODE'] == "prod":
            user_data = get_user_ldap_data(username, current_app.config)

            if user_data["error"]:
                return {"available": False, "error": "%s" % user_data["error"]}

            has_access = False

            if is_admin:
                has_access = True

            if (set(self.allowed_groups) & set(user_data["user_group_ids"])):
                has_access = True
            if (set(self.allowed_groups) & set(user_data["user_group_names"])):
                has_access = True

            if username in self.allowed_users:
                has_access = True
            if user_data['user_id'] in self.allowed_users:
                has_access = True

            # If no restriction on user and groups, check is owner
            if not (self.allowed_users and self.allowed_groups) and str(os.stat(file_path).st_uid) == user_data['user_id']:
                has_access = True

            if not has_access:
                return {"available": False, "error": "User %s does not have permission to publish this file on this repository" % username}
            # Should we have a contact email in this case?

        return {"available": True, "error": ""}

    def publish_file(self, file_path, user_data, version=1, email="", contact="", linked_to=None, tags=set()):
        username = user_data["username"]

        # Send task to copy file
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        size = os.path.getsize(file_path)

        pf = PublishedFile(file_name=file_name, file_path=file_path, repo_path=self.local_path, version=version, owner=username, size=size, version_of=linked_to)
        if tags:
            missing_tag = False
            tag_list = []
            for tag in tags:
                tag_entity = Tag.query.filter_by(tag=tag).first()
                if not tag_entity:
                    missing_tag = True
                    tag_entity = Tag(tag=tag)
                    db.session.add(tag_entity)
                tag_list.append(tag_entity)
            if missing_tag:
                db.session.commit()
            pf.tags = tag_list
        if contact:
            pf.contact = contact
        db.session.add(pf)
        db.session.commit()
        current_app.celery.send_task("publish", (pf.id, file_path, email))
        return pf.id

    def list_files(self):
        # Maybe list all files registered in repos?
        files = PublishedFile.query.filter(PublishedFile.repo_path == self.local_path)
        return files

    def relative_path(self, path):
        return path[len(self.local_path) + 1:]


class Repos():

    def __init__(self, config_file):

        self.config_file = config_file

        self.read_conf(config_file)

    def read_conf(self, path):

        with open(path, 'r') as stream:
            self.repos = self.do_read_conf(stream.read())

    def read_conf_from_str(self, content):

        self.repos = self.do_read_conf(content)

    def do_read_conf(self, content):

        repos = {}
        repos_conf = yaml.safe_load(content)
        if not repos_conf:
            raise ValueError("Malformed repository definition '%s'" % content)

        for repo in repos_conf:
            # We use realpath instead of abspath to resolve symlinks and be sure the user is not doing strange things
            repo_abs = os.path.realpath(repo)
            if not os.path.exists(repo_abs):
                current_app.logger.warning("Directory '%s' does not exist, creating it" % repo_abs)
                os.makedirs(repo_abs)
            if repo_abs in repos:
                raise ValueError('Could not load duplicate repository for path "%s"' % repo_abs)

            for known in repos:
                if self._is_subdir_of(repo_abs, known):
                    raise ValueError('Could not load repository for path "%s", conflicting with "%s"' % (repo_abs, known))

            repos[repo_abs] = Repo(repo_abs, repos_conf[repo])

        return repos

    def _is_subdir_of(self, path1, path2):

        path1 = os.path.join(path1, "")
        path2 = os.path.join(path2, "")

        if path1 == path2:
            return True

        if len(path1) > len(path2):
            if path2 == path1[:len(path2)]:
                return True
        elif len(path1) < len(path2):
            if path1 == path2[:len(path1)]:
                return True

        return False

    def get_repo(self, path):

        path = os.path.join(path, "")

        for repo in self.repos:
            if self.repos[repo].is_in_repo(path):
                return self.repos[repo]

        return False

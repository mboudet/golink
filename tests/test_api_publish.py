import os
import shutil

from golink.extensions import db

from . import GolinkTestCase


class TestApiPublish(GolinkTestCase):

    template_repo = "/golink/test-data/test-repo/"
    testing_repos = ["/repos/myrepo"]
    public_file = "/repos/myrepo/my_file_to_publish.txt"

    def setup_method(self):
        for repo in self.testing_repos:
            if os.path.exists(repo):
                shutil.rmtree(repo)
            shutil.copytree(self.template_repo, repo)

    def teardown_method(self):
        for repo in self.testing_repos:
            if os.path.exists(repo):
                shutil.rmtree(repo)
        db.session.remove()
        db.drop_all()

    def test_publish_missing_token_header(self, app, client):
        """
        Publish without the header
        """
        data = {
            'files': '/foo/bar'
        }
        response = client.post('/api/publish', json=data, headers={'Test': 'some hash'})
        assert response.status_code == 401
        assert response.json == {'error': 'Missing "X-Auth-Token" header'}

    def test_publish_malformed_token_header(self, app, client):
        """
        Publish without the correct header
        """
        data = {
            'files': '/foo/bar'
        }
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'mytoken'})
        assert response.status_code == 401
        assert response.json == {'error': 'Invalid "X-Auth-Token" header: must start with "Bearer "'}

    def test_publish_incorrect_token(self, app, client):
        """
        Publish without the correct token
        """
        data = {
            'files': '/foo/bar'
        }
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhIjoiYiJ9.1bSs1XuNia4apOO73KoixwVRM9YNgU4gdYWeZnAkALY'})

        assert response.status_code == 401
        assert response.json == {'error': 'Invalid token'}

    def test_publish_expired_token(self, app, client):
        """
        Publish with an expired token
        """

        data = {
            'files': '/foo/bar'
        }
        token = self.create_mock_token(app, expire_now=True)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.json == {'error': 'Expired token'}
        assert response.status_code == 401

    def test_publish_missing_body(self, app, client):
        """
        Publish without body
        """
        token = self.create_mock_token(app)
        response = client.post('/api/publish', headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {'error': 'Missing body'}

    def test_publish_missing_path(self, app, client):
        """
        Publish without a proper path
        """
        data = {
            'files': "/foo/bar"
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {'error': 'Missing path'}

    def test_publish_missing_file(self, app, client):
        """
        Publish a missing file
        """
        data = {
            'path': "/foo/bar"
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {'error': 'File not found at path /foo/bar'}

    def test_publish_folder(self, app, client):
        """
        Publish a folder
        """
        path_to_folder = "/repos/myrepo/myfolder"
        os.mkdir(path_to_folder)

        data = {
            'path': path_to_folder
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {'error': 'Path must not be a folder'}

    def test_publish_wrong_email(self, app, client):
        """
        Publish with wrong email address
        """
        data = {
            'path': self.public_file,
            'email': 'x'
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {"error": "The email address is not valid. It must have exactly one @-sign."}

    def test_publish_wrong_contact(self, app, client):
        """
        Publish with wrong email address
        """
        data = {
            'path': self.public_file,
            'contact': 'x'
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json == {"error": "The email address is not valid. It must have exactly one @-sign."}

    def test_publish_link_success(self, app, client):
        """
        Try to publish a file in normal conditions
        """
        public_file = "/repos/myrepo/my_file_to_publish.txt"

        data = {
            'path': public_file
        }
        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 200
        data = response.json
        assert data['message'] == "File registering. It should be ready soon"
        assert 'file_id' in data

    def test_update_malformed_id(self, app, client):
        public_file = "/repos/myrepo/my_file_to_publish.txt"

        data = {
            'path': public_file,
            'linked_to': "fakeid"
        }

        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 400
        assert response.json['error'] == "linked_to fakeid is not a valid id"

    def test_update_wrong_id(self, app, client):
        public_file = "/repos/myrepo/my_file_to_publish.txt"

        data = {
            'path': public_file,
            'linked_to': "f2ecc13f-3038-4f78-8c84-ab881a0b567d"
        }

        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 404
        assert response.json['error'] == "linked_to f2ecc13f-3038-4f78-8c84-ab881a0b567d file does not exists"

    def test_update(self, app, client):
        file_id = self.create_mock_published_file("available")

        public_file = "/repos/myrepo/my_file_to_publish.txt"
        data = {
            'path': public_file,
            'linked_to': file_id
        }

        token = self.create_mock_token(app)
        response = client.post('/api/publish', json=data, headers={'X-Auth-Token': 'Bearer ' + token})

        assert response.status_code == 200
        data = response.json
        assert data['message'] == "File registering. It should be ready soon"
        assert 'file_id' in data

        assert data['version'] == 2

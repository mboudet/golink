import os
import shutil

from golink.extensions import db

from . import GolinkTestCase


class TestApiSearch(GolinkTestCase):
    template_repo = "/gopublish/test-data/test-repo/"
    testing_repo = "/repos/myrepo"
    public_file = "/repos/myrepo/my_file_to_publish.txt"

    def setup_method(self):
        if os.path.exists(self.testing_repo):
            shutil.rmtree(self.testing_repo)
        shutil.copytree(self.template_repo, self.testing_repo)

    def teardown_method(self):
        if os.path.exists(self.testing_repo):
            shutil.rmtree(self.testing_repo)
        db.session.remove()
        db.drop_all()

    def test_search_wrong_term(self, client):
        self.create_mock_published_file("available")

        url = "/api/search?file=blablabloblo"
        response = client.get(url)

        assert response.status_code == 200

        data = response.json['files']

        assert len(data) == 0

    def test_search_term(self, client):
        file_id = self.create_mock_published_file("available")
        size = os.path.getsize(self.public_file)

        url = "/api/search?file=my_file_to_publish"
        response = client.get(url)

        assert response.status_code == 200

        data = response.json['files']

        data[0].pop('publishing_date', None)

        assert len(data) == 1
        assert data[0] == {
            'uri': file_id,
            'file_name': "my_file_to_publish.txt",
            'size': size,
            'version': 1,
            'downloads': 0,
            'status': "available",
            "tags": []
        }

    def test_search_wrong_tags(self, client):
        self.create_mock_published_file("available", tags=["tag1"])

        url = "/api/search"
        response = client.get(url, query_string={'tags': ['blabla']})

        assert response.status_code == 200

        data = response.json['files']
        assert data == []

    def test_search_tags(self, client):
        self.create_mock_published_file("available", tags=["tag2"])
        file_id = self.create_mock_published_file("available", tags=["tag1"])
        size = os.path.getsize(self.public_file)

        url = "/api/search"
        response = client.get(url, query_string={'tags': ['tag1']})

        assert response.status_code == 200

        data = response.json['files']

        assert len(data) == 1
        data[0].pop('publishing_date', None)

        assert data[0] == {
            'uri': file_id,
            'file_name': "my_file_to_publish.txt",
            'size': size,
            'version': 1,
            'downloads': 0,
            'status': "available",
            "tags": ["tag1"]
        }

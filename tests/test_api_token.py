import jwt

from . import GopublishTestCase


class TestApiToken(GopublishTestCase):

    def test_get_token_no_body(self, client):
        """
        Get token without a body
        """
        url = "/api/token/create"

        response = client.post(url)

        assert response.status_code == 400
        assert response.json.get("error") == "Missing body"

    def test_get_token_no_username(self, client):
        """
        Get a token without a username
        """
        body = {"password": "xxx"}
        url = "/api/token/create"

        response = client.post(url, json=body)

        assert response.status_code == 400
        assert response.json.get("error") == "Missing either username or password in body"

    def test_get_token_no_password(self, client):
        """
        Get a token without a password
        """
        body = {"username": "xxx"}
        url = "/api/token/create"

        response = client.post(url, json=body)

        assert response.status_code == 400
        assert response.json.get("error") == "Missing either username or password in body"

    def test_get_token(self, app, client):
        """
        Get a token
        """
        body = {"username": "root", "password": "xxx"}
        url = "/api/token/create"

        response = client.post(url, json=body)

        assert response.status_code == 200
        assert response.json.get("token")

        payload = jwt.decode(response.json.get("token"), app.config['SECRET_KEY'], algorithms=["HS256"])
        assert payload['username'] == "root"

import pytest
from app import create_app
from app.database import db
from app.models.url import ShortURL, generate_code, is_valid_url

@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    with application.app_context():
        db.create_tables([ShortURL], safe=True)
    yield application
    with application.app_context():
        db.drop_tables([ShortURL], safe=True)

@pytest.fixture
def client(app):
    return app.test_client()

class TestGenerateCode:
    def test_default_length(self):
        assert len(generate_code()) == 6

    def test_alphanumeric(self):
        assert generate_code().isalnum()

    def test_codes_are_random(self):
        codes = {generate_code() for _ in range(50)}
        assert len(codes) > 45

class TestIsValidUrl:
    def test_valid_https(self):
        assert is_valid_url("https://google.com") is True

    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_empty(self):
        assert is_valid_url("") is False

    def test_invalid_none(self):
        assert is_valid_url(None) is False

    def test_invalid_ftp(self):
        assert is_valid_url("ftp://example.com") is False

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_returns_ok(self, client):
        assert client.get("/health").get_json()["status"] == "ok"

class TestShortenEndpoint:
    def test_shorten_valid_url(self, client):
        r = client.post("/shorten", json={"url": "https://example.com"})
        assert r.status_code == 201

    def test_shorten_returns_code(self, client):
        r = client.post("/shorten", json={"url": "https://example.com"})
        data = r.get_json()
        assert "code" in data and "short_url" in data

    def test_shorten_missing_url(self, client):
        r = client.post("/shorten", json={"other": "stuff"})
        assert r.status_code == 400

    def test_shorten_invalid_url(self, client):
        r = client.post("/shorten", json={"url": "not-a-url"})
        assert r.status_code == 422

    def test_shorten_no_body(self, client):
        r = client.post("/shorten", data="bad", content_type="text/plain")
        assert r.status_code == 400

    def test_shorten_returns_json_error(self, client):
        r = client.post("/shorten", json={"url": ""})
        assert "error" in r.get_json()

class TestRedirectEndpoint:
    def test_redirect_works(self, client):
        code = client.post("/shorten", json={"url": "https://example.com"}).get_json()["code"]
        r = client.get(f"/{code}")
        assert r.status_code == 302
        assert r.headers["Location"] == "https://example.com"

    def test_redirect_not_found(self, client):
        r = client.get("/zzz999")
        assert r.status_code == 404

    def test_redirect_returns_json_error(self, client):
        r = client.get("/zzz999")
        assert "error" in r.get_json()

class TestListEndpoint:
    def test_list_returns_200(self, client):
        assert client.get("/urls").status_code == 200

    def test_list_returns_array(self, client):
        assert isinstance(client.get("/urls").get_json(), list)

class TestErrorHandlers:
    def test_404_returns_json(self, client):
        r = client.get("/this/does/not/exist/at/all")
        assert r.status_code == 404
        assert "error" in r.get_json()

    def test_405_returns_json(self, client):
        r = client.post("/health")
        assert r.status_code == 405
        assert "error" in r.get_json()

import io
import json
import pytest
from app import create_app
from app.database import db
from app.models.user import User
from app.models.url import URL, generate_short_code
from app.models.event import Event


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    with application.app_context():
        db.create_tables([User, URL, Event], safe=True)
    yield application
    with application.app_context():
        db.drop_tables([Event, URL, User], safe=True)


@pytest.fixture
def client(app):
    return app.test_client()


USERS_CSV = """id,username,email,created_at
1,silvertrail15,silvertrail15@hackstack.io,2025-09-19 22:25:05
2,urbancanyon36,urbancanyon36@opswise.net,2024-04-09 02:51:03
"""

URLS_CSV = """id,user_id,short_code,original_url,title,is_active,created_at,updated_at
1,1,ALQRog,https://opswise.net/harbor/journey/1,Service guide lagoon,True,2025-06-04 00:07:00,2025-11-19 03:17:29
2,2,BXRTop,https://example.com/test/2,Another test,True,2025-06-05 00:07:00,2025-11-20 03:17:29
"""

EVENTS_CSV = """id,url_id,user_id,event_type,timestamp,details
1,1,1,created,2025-06-04 00:07:00,"{""short_code"":""ALQRog"",""original_url"":""https://opswise.net/harbor/journey/1""}"
"""


class TestHealth:
    def test_health_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_status_ok(self, client):
        assert client.get("/health").get_json()["status"] == "ok"


class TestGenerateShortCode:
    def test_length(self):
        assert len(generate_short_code()) == 6

    def test_alphanumeric(self):
        assert generate_short_code().isalnum()

    def test_random(self):
        codes = {generate_short_code() for _ in range(50)}
        assert len(codes) > 45


class TestUsersBulk:
    def test_bulk_import_returns_200_or_201(self, client):
        data = {"file": (io.BytesIO(USERS_CSV.encode()), "users.csv")}
        r = client.post("/users/bulk", data=data, content_type="multipart/form-data")
        assert r.status_code in (200, 201)

    def test_bulk_import_returns_count(self, client):
        data = {"file": (io.BytesIO(USERS_CSV.encode()), "users.csv")}
        r = client.post("/users/bulk", data=data, content_type="multipart/form-data")
        body = r.get_json()
        assert "count" in body or "imported" in body

    def test_bulk_no_file_returns_400(self, client):
        r = client.post("/users/bulk", data={}, content_type="multipart/form-data")
        assert r.status_code == 400


class TestListUsers:
    def test_list_returns_200(self, client):
        assert client.get("/users").status_code == 200

    def test_list_returns_array(self, client):
        assert isinstance(client.get("/users").get_json(), list)

    def test_list_shows_imported_users(self, client):
        data = {"file": (io.BytesIO(USERS_CSV.encode()), "users.csv")}
        client.post("/users/bulk", data=data, content_type="multipart/form-data")
        users = client.get("/users").get_json()
        usernames = [u["username"] for u in users]
        assert "silvertrail15" in usernames


class TestGetUser:
    def test_get_existing_user(self, client):
        data = {"file": (io.BytesIO(USERS_CSV.encode()), "users.csv")}
        client.post("/users/bulk", data=data, content_type="multipart/form-data")
        r = client.get("/users/1")
        assert r.status_code == 200
        assert r.get_json()["username"] == "silvertrail15"

    def test_get_nonexistent_returns_404(self, client):
        assert client.get("/users/99999").status_code == 404


class TestCreateUser:
    def test_create_valid_user(self, client):
        r = client.post("/users", json={"username": "testuser", "email": "test@example.com"})
        assert r.status_code == 201

    def test_create_returns_user_object(self, client):
        r = client.post("/users", json={"username": "newuser", "email": "new@example.com"})
        data = r.get_json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "created_at" in data

    def test_create_invalid_username_type(self, client):
        r = client.post("/users", json={"username": 123, "email": "test@example.com"})
        assert r.status_code in (400, 422)

    def test_create_missing_username(self, client):
        r = client.post("/users", json={"email": "test@example.com"})
        assert r.status_code in (400, 422)

    def test_create_no_body(self, client):
        r = client.post("/users", data="bad", content_type="text/plain")
        assert r.status_code == 400


class TestUpdateUser:
    def test_update_username(self, client):
        client.post("/users", json={"username": "original", "email": "orig@example.com"})
        users = client.get("/users").get_json()
        uid = users[0]["id"]
        r = client.put(f"/users/{uid}", json={"username": "updated_username"})
        assert r.status_code == 200
        assert r.get_json()["username"] == "updated_username"

    def test_update_nonexistent_returns_404(self, client):
        assert client.put("/users/99999", json={"username": "x"}).status_code == 404


class TestCreateURL:
    def test_create_valid_url(self, client):
        client.post("/users", json={"username": "urluser", "email": "url@example.com"})
        users = client.get("/users").get_json()
        uid = users[0]["id"]
        r = client.post("/urls", json={
            "user_id": uid,
            "original_url": "https://example.com/test",
            "title": "Test URL"
        })
        assert r.status_code == 201

    def test_create_returns_short_code(self, client):
        r = client.post("/urls", json={"original_url": "https://example.com"})
        data = r.get_json()
        assert "short_code" in data
        assert "id" in data

    def test_create_missing_url_returns_400(self, client):
        r = client.post("/urls", json={"title": "no url"})
        assert r.status_code == 400

    def test_create_invalid_url_returns_422(self, client):
        r = client.post("/urls", json={"original_url": "not-a-url"})
        assert r.status_code == 422

    def test_create_missing_user_returns_404(self, client):
        r = client.post("/urls", json={"original_url": "https://example.com", "user_id": 99999})
        assert r.status_code == 404


class TestListURLs:
    def test_list_returns_200(self, client):
        assert client.get("/urls").status_code == 200

    def test_list_returns_array(self, client):
        assert isinstance(client.get("/urls").get_json(), list)

    def test_list_filter_by_user_id(self, client):
        data = {"file": (io.BytesIO(USERS_CSV.encode()), "users.csv")}
        client.post("/users/bulk", data=data, content_type="multipart/form-data")
        data = {"file": (io.BytesIO(URLS_CSV.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        r = client.get("/urls?user_id=1")
        urls = r.get_json()
        assert all(u["user_id"] == 1 for u in urls)


class TestGetURL:
    def test_get_existing_url(self, client):
        data = {"file": (io.BytesIO(URLS_CSV.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        r = client.get("/urls/1")
        assert r.status_code == 200
        assert r.get_json()["short_code"] == "ALQRog"

    def test_get_nonexistent_returns_404(self, client):
        assert client.get("/urls/99999").status_code == 404


class TestUpdateURL:
    def test_update_title_and_status(self, client):
        data = {"file": (io.BytesIO(URLS_CSV.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        r = client.put("/urls/1", json={"title": "Updated Title", "is_active": False})
        assert r.status_code == 200
        body = r.get_json()
        assert body["title"] == "Updated Title"
        assert body["is_active"] is False

    def test_update_nonexistent_returns_404(self, client):
        assert client.put("/urls/99999", json={"title": "x"}).status_code == 404


class TestRedirect:
    def test_redirect_works(self, client):
        data = {"file": (io.BytesIO(URLS_CSV.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        r = client.get("/ALQRog")
        assert r.status_code == 302
        assert "opswise.net" in r.headers["Location"]

    def test_redirect_not_found(self, client):
        assert client.get("/zzz999").status_code == 404

    def test_redirect_inactive_returns_410(self, client):
        data = {"file": (io.BytesIO(URLS_CSV.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        client.put("/urls/1", json={"is_active": False})
        r = client.get("/ALQRog")
        assert r.status_code == 410


class TestEvents:
    def test_events_returns_200(self, client):
        assert client.get("/events").status_code == 200

    def test_events_returns_array(self, client):
        assert isinstance(client.get("/events").get_json(), list)

    def test_create_url_generates_event(self, client):
        client.post("/urls", json={"original_url": "https://example.com"})
        events = client.get("/events").get_json()
        assert len(events) >= 1
        assert any(e["event_type"] == "created" for e in events)


class TestErrorHandlers:
    def test_404_returns_json(self, client):
        r = client.get("/this/route/does/not/exist/at/all")
        assert r.status_code == 404
        assert "error" in r.get_json()

    def test_405_returns_json(self, client):
        r = client.post("/health")
        assert r.status_code == 405
        assert "error" in r.get_json()

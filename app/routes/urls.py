import csv
import datetime
import io
import json

from flask import Blueprint, jsonify, redirect, request
from app.models.url import URL, generate_short_code
from app.models.event import Event
from app.models.user import User
from app.database import db

urls_bp = Blueprint("urls", __name__)


def url_to_dict(u):
    return {
        "id": u.id,
        "user_id": u.user_id,
        "short_code": u.short_code,
        "original_url": u.original_url,
        "title": u.title,
        "is_active": u.is_active,
        "created_at": u.created_at.strftime("%Y-%m-%dT%H:%M:%S") if u.created_at else None,
        "updated_at": u.updated_at.strftime("%Y-%m-%dT%H:%M:%S") if u.updated_at else None,
    }


@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    user_id = request.args.get("user_id", type=int)
    query = URL.select().order_by(URL.id)
    if user_id:
        query = query.where(URL.user_id == user_id)
    return jsonify([url_to_dict(u) for u in query]), 200


@urls_bp.route("/urls/<int:url_id>", methods=["GET"])
def get_url(url_id):
    try:
        url = URL.get_by_id(url_id)
        return jsonify(url_to_dict(url)), 200
    except URL.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    original_url = data.get("original_url", "").strip()
    if not original_url:
        return jsonify({"error": "original_url is required"}), 400

    if not original_url.startswith(("http://", "https://")):
        return jsonify({"error": "original_url must start with http:// or https://"}), 422

    user_id = data.get("user_id")
    if user_id is not None:
        if not User.select().where(User.id == user_id).exists():
            return jsonify({"error": f"User {user_id} not found"}), 404

    title = data.get("title")

    for _ in range(5):
        code = generate_short_code()
        if not URL.select().where(URL.short_code == code).exists():
            break
    else:
        return jsonify({"error": "Could not generate unique short code"}), 500

    now = datetime.datetime.now()
    url = URL.create(
        user_id=user_id,
        short_code=code,
        original_url=original_url,
        title=title,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    Event.create(
        url_id=url.id,
        user_id=user_id,
        event_type="created",
        timestamp=now,
        details=json.dumps({"short_code": code, "original_url": original_url}),
    )

    return jsonify(url_to_dict(url)), 201


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    try:
        url = URL.get_by_id(url_id)
    except URL.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "title" in data:
        url.title = data["title"]
    if "is_active" in data:
        url.is_active = bool(data["is_active"])
    if "original_url" in data:
        url.original_url = data["original_url"]

    url.updated_at = datetime.datetime.now()
    url.save()
    return jsonify(url_to_dict(url)), 200


@urls_bp.route("/urls/bulk", methods=["POST"])
def bulk_urls():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    imported = []
    with db.atomic():
        for row in reader:
            def parse_dt(val):
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.datetime.strptime(val.strip(), fmt)
                    except (ValueError, AttributeError):
                        pass
                return datetime.datetime.now()

            is_active = str(row.get("is_active", "True")).strip().lower() not in ("false", "0", "no")

            url, created = URL.get_or_create(
                id=int(row["id"]),
                defaults={
                    "user_id": int(row["user_id"]) if row.get("user_id") else None,
                    "short_code": row["short_code"],
                    "original_url": row["original_url"],
                    "title": row.get("title"),
                    "is_active": is_active,
                    "created_at": parse_dt(row.get("created_at", "")),
                    "updated_at": parse_dt(row.get("updated_at", "")),
                }
            )
            if created:
                imported.append(url_to_dict(url))

    return jsonify({"imported": len(imported), "count": len(imported)}), 201


@urls_bp.route("/<short_code>")
def redirect_url(short_code):
    if not short_code or len(short_code) > 10:
        return jsonify({"error": "Invalid short code"}), 400

    try:
        url = URL.get(URL.short_code == short_code)
    except URL.DoesNotExist:
        return jsonify({"error": "Short URL not found"}), 404

    if not url.is_active:
        return jsonify({"error": "This short URL has been deactivated"}), 410

    URL.update(updated_at=datetime.datetime.now()).where(URL.short_code == short_code).execute()

    Event.create(
        url_id=url.id,
        user_id=url.user_id,
        event_type="visited",
        timestamp=datetime.datetime.now(),
        details=json.dumps({"short_code": short_code}),
    )

    return redirect(url.original_url, code=302)

import csv
import datetime
import io
import json

from flask import Blueprint, jsonify, request
from app.models.event import Event
from app.database import db

events_bp = Blueprint("events", __name__)


def event_to_dict(e):
    details = None
    if e.details:
        try:
            details = json.loads(e.details)
        except (ValueError, TypeError):
            details = e.details

    return {
        "id": e.id,
        "url_id": e.url_id,
        "user_id": e.user_id,
        "event_type": e.event_type,
        "timestamp": e.timestamp.strftime("%Y-%m-%dT%H:%M:%S") if e.timestamp else None,
        "details": details,
    }


@events_bp.route("/events", methods=["GET"])
def list_events():
    url_id = request.args.get("url_id", type=int)
    event_type = request.args.get("event_type")

    query = Event.select().order_by(Event.id)

    if url_id is not None:
        query = query.where(Event.url_id == url_id)
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    return jsonify([event_to_dict(e) for e in query]), 200


@events_bp.route("/events", methods=["POST"])
def create_event():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    event_type = data.get("event_type")
    if not event_type or not isinstance(event_type, str):
        return jsonify({"error": "event_type is required and must be a string"}), 422

    uurl_id = data.get("url_id")
    if url_id is not None and not isinstance(url_id, int):
        return jsonify({"error": "url_id must be an integer"}), 422

    user_id = data.get("user_id")
    if user_id is not None and not isinstance(user_id, int):
        return jsonify({"error": "user_id must be an integer"}), 422

    details = data.get("details")
    if details is not None and not isinstance(details, dict):
        return jsonify({"error": "details must be a JSON object"}), 422

    if details is not None and not isinstance(details, dict):
        return jsonify({"error": "details must be a JSON object"}), 422

    try:
        event = Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.datetime.now(),
            details=json.dumps(details) if details else None,
        )
        return jsonify(event_to_dict(event)), 201
    except Exception:
        db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events))")
        event = Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.datetime.now(),
            details=json.dumps(details) if details else None,
        )
        return jsonify(event_to_dict(event)), 201


@events_bp.route("/events/bulk", methods=["POST"])
def bulk_events():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    imported = 0
    with db.atomic():
        for row in reader:
            try:
                ts = datetime.datetime.strptime(row.get("timestamp", "").strip(), "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                ts = datetime.datetime.now()

            db.execute_sql(
                """
                INSERT INTO events (id, url_id, user_id, event_type, timestamp, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    int(row["id"]),
                    int(row["url_id"]) if row.get("url_id") else None,
                    int(row["user_id"]) if row.get("user_id") else None,
                    row.get("event_type", ""),
                    ts,
                    row.get("details"),
                )
            )
            imported += 1

    db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events))")
    return jsonify({"imported": imported, "count": imported}), 201

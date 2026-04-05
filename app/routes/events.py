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
    events = Event.select().order_by(Event.id)
    return jsonify([event_to_dict(e) for e in events]), 200


@events_bp.route("/events/bulk", methods=["POST"])
def bulk_events():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    imported = []
    with db.atomic():
        for row in reader:
            try:
                ts = datetime.datetime.strptime(row.get("timestamp", "").strip(), "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                ts = datetime.datetime.now()

            event, created = Event.get_or_create(
                id=int(row["id"]),
                defaults={
                    "url_id": int(row["url_id"]) if row.get("url_id") else None,
                    "user_id": int(row["user_id"]) if row.get("user_id") else None,
                    "event_type": row.get("event_type", ""),
                    "timestamp": ts,
                    "details": row.get("details"),
                }
            )
            if created:
                imported.append(event_to_dict(event))

    return jsonify({"imported": len(imported), "count": len(imported)}), 201

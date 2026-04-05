import csv
import datetime
import io

from flask import Blueprint, jsonify, request
from app.models.user import User
from app.database import db

users_bp = Blueprint("users", __name__)


def user_to_dict(u):
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "created_at": u.created_at.strftime("%Y-%m-%dT%H:%M:%S") if u.created_at else None,
    }


@users_bp.route("/users", methods=["GET"])
def list_users():
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", 20, type=int)
    query = User.select().order_by(User.id)
    if page:
        query = query.paginate(page, per_page)
    return jsonify([user_to_dict(u) for u in query]), 200


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
        return jsonify(user_to_dict(user)), 200
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get("username")
    email = data.get("email")

    if not username or not isinstance(username, str):
        return jsonify({"error": "username is required and must be a string"}), 422
    if not email or not isinstance(email, str):
        return jsonify({"error": "email is required and must be a string"}), 422

    if User.select().where(User.username == username).exists():
        return jsonify({"error": "username already exists"}), 409
    if User.select().where(User.email == email).exists():
        return jsonify({"error": "email already exists"}), 409

    try:
        user = User.create(username=username, email=email)
        return jsonify(user_to_dict(user)), 201
    except Exception:
        db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
        user = User.create(username=username, email=email)
        return jsonify(user_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "username" in data:
        if not isinstance(data["username"], str):
            return jsonify({"error": "username must be a string"}), 422
        user.username = data["username"]
    if "email" in data:
        if not isinstance(data["email"], str):
            return jsonify({"error": "email must be a string"}), 422
        user.email = data["email"]

    user.save()
    return jsonify(user_to_dict(user)), 200


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user = User.get_by_id(user_id)
        user.delete_instance()
        return jsonify({"message": f"User {user_id} deleted"}), 200
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_users():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    imported = 0
    with db.atomic():
        for row in rows:
            try:
                created_at = datetime.datetime.strptime(
                    row.get("created_at", "").strip(), "%Y-%m-%d %H:%M:%S"
                )
            except (ValueError, AttributeError):
                created_at = datetime.datetime.now()

            db.execute_sql(
                """
                INSERT INTO users (id, username, email, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (int(row["id"]), row["username"], row["email"], created_at)
            )
            imported += 1

    db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
    return jsonify({"imported": imported, "count": imported}), 201

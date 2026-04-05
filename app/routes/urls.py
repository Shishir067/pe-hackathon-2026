from flask import Blueprint, jsonify, redirect, request
from playhouse.shortcuts import model_to_dict
from app.models.url import ShortURL, generate_code, is_valid_url

urls_bp = Blueprint("urls", __name__)

@urls_bp.route("/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    target = data.get("url", "").strip()
    if not target:
        return jsonify({"error": "Field 'url' is required"}), 400
    if not is_valid_url(target):
        return jsonify({"error": "Invalid URL. Must start with http:// or https://"}), 422
    for _ in range(5):
        code = generate_code()
        if not ShortURL.select().where(ShortURL.code == code).exists():
            break
    else:
        return jsonify({"error": "Could not generate unique code, try again"}), 500
    url = ShortURL.create(code=code, target=target)
    return jsonify({"code": url.code, "short_url": f"/{url.code}", "target": url.target}), 201

@urls_bp.route("/<code>")
def redirect_url(code):
    if not code or len(code) > 10:
        return jsonify({"error": "Invalid code"}), 400
    try:
        url = ShortURL.get(ShortURL.code == code)
    except ShortURL.DoesNotExist:
        return jsonify({"error": "Short URL not found"}), 404
    if not url.is_active:
        return jsonify({"error": "This short URL has been deactivated"}), 410
    ShortURL.update(hits=ShortURL.hits + 1).where(ShortURL.code == code).execute()
    return redirect(url.target, code=302)

@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    urls = ShortURL.select().where(ShortURL.is_active == True).order_by(ShortURL.created_at.desc())
    return jsonify([model_to_dict(u) for u in urls]), 200

@urls_bp.route("/urls/<code>", methods=["GET"])
def get_url(code):
    try:
        url = ShortURL.get(ShortURL.code == code)
        return jsonify(model_to_dict(url)), 200
    except ShortURL.DoesNotExist:
        return jsonify({"error": "Not found"}), 404

@urls_bp.route("/urls/<code>", methods=["DELETE"])
def delete_url(code):
    try:
        url = ShortURL.get(ShortURL.code == code)
        url.is_active = False
        url.save()
        return jsonify({"message": f"Short URL '{code}' deactivated"}), 200
    except ShortURL.DoesNotExist:
        return jsonify({"error": "Not found"}), 404

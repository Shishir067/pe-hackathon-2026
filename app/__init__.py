from dotenv import load_dotenv
from flask import Flask, jsonify
from app.database import init_db
from app.routes import register_routes

def create_app():
    load_dotenv()
    app = Flask(__name__)
    init_db(app)
    from app import models  # noqa: F401
    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "status": 405}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error", "status": 500}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred", "status": 500}), 500

    return app

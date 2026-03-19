from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.analysis import analysis_bp
from routes.chatbot import chatbot_bp
from routes.routines import routine_bp
from routes.products import products_bp
from routes.report import report_bp
import os
import threading


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:5174",
                "https://lumera-wheat.vercel.app",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    })

    db.init_app(app)
    jwt = JWTManager(app)

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        print(f"❌ JWT invalid token: {reason}")
        return {'error': f'Invalid token: {reason}'}, 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print("❌ JWT expired token")
        return {'error': 'Token has expired. Please log in again.'}, 401

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        print(f"❌ JWT unauthorized: {reason}")
        return {'error': f'Unauthorized: {reason}'}, 401

    app.register_blueprint(auth_bp,     url_prefix='/api/auth')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(chatbot_bp,  url_prefix='/api/chatbot')
    app.register_blueprint(routine_bp,  url_prefix='/api/routines')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(report_bp,   url_prefix='/api/report')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        print("✓ Database tables created")

        def _load_models_background():
            try:
                from download_models import download_models
                download_models()
            except Exception as e:
                print(f"⚠ Model download failed: {e}")

            try:
                from services.ml_service import get_analyzer
                analyzer = get_analyzer()
                if analyzer.model is not None:
                    print(f"✓ Skin type model ready — classes: {analyzer.skin_types}")
                else:
                    print("⚠ Skin type model not found — using feature-based fallback")
            except Exception as e:
                print(f"⚠ Could not load skin model: {e}")

            try:
                from skin_concern_detector import SkinConcernDetector
                detector = SkinConcernDetector()
                ensemble = detector._load_ensemble()
                if ensemble:
                    for _, weight, name in ensemble:
                        print(f"✓ Concern model ready: {name} (weight={weight})")
                else:
                    print("⚠ No concern models found — CV-only detection will be used")
            except Exception as e:
                print(f"⚠ Could not load concern models: {e}")

            print("✅ All models loaded and ready")

        thread = threading.Thread(target=_load_models_background, daemon=True)
        thread.start()
        print("⏳ ML models loading in background...")

    @app.route('/api/health', methods=['GET'])
    def health():
        return {'status': 'ok', 'message': 'Backend is running'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting backend on http://localhost:3001")
    port = int(os.environ.get('PORT', 3001))
    app.run(debug=False, host='0.0.0.0', port=port)
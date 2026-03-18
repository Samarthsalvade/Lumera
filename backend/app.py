#app.py
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.analysis import analysis_bp
from routes.chatbot import chatbot_bp
import os
from routes.report import report_bp
from routes.routines import routine_bp
from routes.products import products_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    })

    db.init_app(app)
    jwt = JWTManager(app)

    # JWT error handlers
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

    # Blueprints
    app.register_blueprint(auth_bp,     url_prefix='/api/auth')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(chatbot_bp,  url_prefix='/api/chatbot')
    app.register_blueprint(routine_bp, url_prefix='/api/routines')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(report_bp, url_prefix='/api/report') 
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        print("✓ Database tables created")

    @app.route('/api/health', methods=['GET'])
    def health():
        return {'status': 'ok', 'message': 'Backend is running'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting backend on http://localhost:3001")
    app.run(debug=True, host='0.0.0.0', port=3001)

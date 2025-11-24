"""
Flask Application for Face Attendance System
Main entry point for the web application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from config import get_config
from models import db
from datetime import datetime
import os

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMPLATE_FOLDER'], exist_ok=True)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Register blueprints
    from routes.api import api_bp
    from routes.web import web_bp

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(web_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500
    
    # Register template filters
    from utils import convert_utc_to_local
    
    @app.template_filter('local_time')
    def local_time_filter(dt, format='%Y-%m-%d %H:%M:%S'):
        """
        Template filter to convert UTC datetime to local timezone
        
        Usage in templates:
            {{ record.timestamp | local_time }}
            {{ record.timestamp | local_time('%I:%M %p') }}
        """
        local_dt = convert_utc_to_local(dt)
        if local_dt is None:
            return 'N/A'
        return local_dt.strftime(format)

    # Context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )

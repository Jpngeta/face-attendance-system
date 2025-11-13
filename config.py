"""
Configuration management for Face Attendance System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base configuration class"""

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_APP = os.getenv('FLASK_APP', 'app.py')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/attendance.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Camera Configuration
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', 640))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', 480))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', 30))

    # Face Recognition Configuration
    DETECTION_SIZE = int(os.getenv('DETECTION_SIZE', 320))
    RECOGNITION_THRESHOLD = float(os.getenv('RECOGNITION_THRESHOLD', 20))
    PROCESS_EVERY_N_FRAMES = int(os.getenv('PROCESS_EVERY_N_FRAMES', 2))

    # InsightFace Configuration
    INSIGHTFACE_MODEL = 'buffalo_l'
    INSIGHTFACE_DET_SIZE = (DETECTION_SIZE, DETECTION_SIZE)
    EXECUTION_PROVIDER = 'CPUExecutionProvider'

    # Dataset Configuration
    DATASET_PATH = BASE_DIR / 'insightface_dataset'
    ENCODINGS_FILE = BASE_DIR / 'insightface_encodings.pkl'

    # Attendance Configuration
    AUTO_MARK_ATTENDANCE = os.getenv('AUTO_MARK_ATTENDANCE', 'true').lower() == 'true'
    ATTENDANCE_COOLDOWN_MINUTES = int(os.getenv('ATTENDANCE_COOLDOWN_MINUTES', 5))
    SESSION_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT_MINUTES', 60))

    # Google Sheets Configuration
    GOOGLE_SHEETS_ENABLED = os.getenv('GOOGLE_SHEETS_ENABLED', 'false').lower() == 'true'
    GOOGLE_CREDENTIALS_FILE = BASE_DIR / os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')

    # Server Configuration
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    # Static and Template Folders
    STATIC_FOLDER = BASE_DIR / 'static'
    TEMPLATE_FOLDER = BASE_DIR / 'templates'

    # Upload Configuration
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

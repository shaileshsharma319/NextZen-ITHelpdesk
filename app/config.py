import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development').lower()
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if FLASK_ENV == 'production':
            raise RuntimeError('SECRET_KEY is required in production.')
        SECRET_KEY = 'dev-secret-key'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI and FLASK_ENV == 'production':
        raise RuntimeError('DATABASE_URL is required in production.')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'app', 'static', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 21 * 1024 * 1024))

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    EMAIL_AUTO_FETCH_ENABLED = os.environ.get('EMAIL_AUTO_FETCH_ENABLED', 'True') == 'True'
    EMAIL_AUTO_FETCH_INTERVAL_SECONDS = int(os.environ.get('EMAIL_AUTO_FETCH_INTERVAL_SECONDS', 600))

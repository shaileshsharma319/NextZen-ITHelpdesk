from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from app.utils.formatting import email_content
    app.jinja_env.filters['email_content'] = email_content

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    from app.routes.auth import auth
    from app.routes.dashboard import dashboard
    from app.routes.tickets import tickets
    from app.routes.admin import admin
    from app.routes.assets import assets
    from app.routes.knowledge import knowledge
    from app.routes.departments import departments
    from app.routes.software import software
    from app.routes.settings import settings
    from app.routes.audit import audit

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(dashboard, url_prefix='/')
    app.register_blueprint(tickets, url_prefix='/tickets')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(assets, url_prefix='/assets')
    app.register_blueprint(knowledge, url_prefix='/knowledge')
    app.register_blueprint(departments, url_prefix='/departments')
    app.register_blueprint(software, url_prefix='/software')
    app.register_blueprint(settings, url_prefix='/settings')
    app.register_blueprint(audit, url_prefix='/audit')

    with app.app_context():
        from app.models import email_config, user_signature, audit as audit_models  # noqa: ensure tables created
        from app.utils.schema import ensure_helpdesk_schema
        db.create_all()
        ensure_helpdesk_schema()

    return app

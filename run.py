from app import create_app
import os

app = create_app()

def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

if __name__ == '__main__':
    from app.utils.email_scheduler import start_email_auto_fetch

    debug = env_bool('FLASK_DEBUG', False)
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_email_auto_fetch(app)
    app.run(
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(os.environ.get('FLASK_PORT', 5000)),
        debug=debug,
    )

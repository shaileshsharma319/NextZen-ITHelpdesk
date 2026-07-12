import threading

from app import db
from app.utils.email import fetch_inbound_email_tickets

_scheduler_lock = threading.Lock()
_scheduler_started = False
_stop_event = threading.Event()


def _fetch_loop(app, interval_seconds):
    initial_delay = min(10, interval_seconds)
    if _stop_event.wait(initial_delay):
        return

    while not _stop_event.is_set():
        with app.app_context():
            try:
                created, error = fetch_inbound_email_tickets()
                if error and error not in ('Inbound email is not enabled.', 'IMAP settings are incomplete.'):
                    app.logger.warning('Auto email fetch failed: %s', error)
                elif created:
                    app.logger.info('Auto email fetch imported %s ticket(s).', created)
            except Exception:
                app.logger.exception('Auto email fetch crashed.')
            finally:
                db.session.remove()

        if _stop_event.wait(interval_seconds):
            break


def start_email_auto_fetch(app):
    global _scheduler_started

    if not app.config.get('EMAIL_AUTO_FETCH_ENABLED', True):
        return False

    interval_seconds = max(60, int(app.config.get('EMAIL_AUTO_FETCH_INTERVAL_SECONDS', 600)))

    with _scheduler_lock:
        if _scheduler_started:
            return False

        thread = threading.Thread(
            target=_fetch_loop,
            args=(app, interval_seconds),
            name='helpdesk-email-auto-fetch',
            daemon=True,
        )
        thread.start()
        _scheduler_started = True
        app.logger.info('Auto email fetch scheduler started. Interval: %s seconds.', interval_seconds)
        return True

import signal
from threading import Event

from app import create_app
from app.utils.email_scheduler import start_email_auto_fetch


stop_event = Event()


def stop_worker(signum, frame):
    stop_event.set()


def main():
    app = create_app()
    start_email_auto_fetch(app)

    while not stop_event.is_set():
        stop_event.wait(5)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)
    main()

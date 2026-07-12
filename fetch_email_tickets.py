from app import create_app
from app.utils.email import fetch_inbound_email_tickets

app = create_app()
with app.app_context():
    created, error = fetch_inbound_email_tickets()
    if error:
        print(f'Email fetch failed: {error}')
    else:
        print(f'{created} email ticket(s) imported.')

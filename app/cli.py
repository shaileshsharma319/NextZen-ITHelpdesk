import click

from app import db
from app.models.department import Department
from app.models.user import User
from app.utils.departments import STANDARD_DEPARTMENTS


def register_cli_commands(app):
    @app.cli.command('init-defaults')
    def init_defaults():
        """Create required default records without demo/sample data."""
        created = 0

        for item in STANDARD_DEPARTMENTS:
            department = Department.query.filter_by(name=item['name']).first()
            if department:
                continue

            db.session.add(Department(
                name=item['name'],
                description=item.get('description'),
                location=item.get('location'),
            ))
            created += 1

        db.session.commit()
        click.echo(f'Default departments ready. Created: {created}')

    @app.cli.command('init-admin')
    @click.option('--email', prompt=True, help='Admin login email address.')
    @click.option('--name', prompt=True, help='Admin display name.')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password.')
    def init_admin(email, name, password):
        """Create the first production admin user."""
        existing = User.query.filter_by(email=email.strip().lower()).first()
        if existing:
            click.echo('Admin user already exists for this email.')
            return

        username = email.split('@', 1)[0].strip().lower()
        if User.query.filter_by(username=username).first():
            username = None

        user = User(
            name=name.strip(),
            first_name=name.strip().split(' ', 1)[0],
            last_name=name.strip().split(' ', 1)[1] if ' ' in name.strip() else '',
            email=email.strip().lower(),
            username=username,
            role='master_admin',
            allow_helpdesk_admin=True,
            allow_inventory=True,
            allow_licenses=True,
            allow_compliance=True,
            two_factor_required=True,
            company_domain=email.split('@', 1)[1].lower() if '@' in email else None,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        click.echo('Production admin created. MFA will be required on first login.')

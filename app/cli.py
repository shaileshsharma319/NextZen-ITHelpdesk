import click

from app import db
from app.models.department import Department
from app.models.user import User
from app.utils.departments import STANDARD_DEPARTMENTS


def ensure_default_departments():
    created = 0
    departments = {}

    for item in STANDARD_DEPARTMENTS:
        department = Department.query.filter_by(name=item['name']).first()
        if not department:
            department = Department(
                name=item['name'],
                description=item.get('description'),
                location=item.get('location'),
            )
            db.session.add(department)
            db.session.flush()
            created += 1
        departments[item['name']] = department

    return departments, created


def register_cli_commands(app):
    @app.cli.command('init-defaults')
    def init_defaults():
        """Create required default records without demo/sample data."""
        departments, created = ensure_default_departments()
        db.session.commit()
        click.echo(f'Default departments ready. Created: {created}')

    @app.cli.command('init-admin')
    @click.option('--email', prompt=True, help='Admin login email address.')
    @click.option('--name', prompt=True, help='Admin display name.')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password.')
    @click.option('--department', default='IT Department', show_default=True, help='Department assigned to the admin user.')
    def init_admin(email, name, password, department):
        """Create the first production admin user."""
        departments, created = ensure_default_departments()
        admin_department = Department.query.filter_by(name=department).first() or departments.get('IT Department')
        email = email.strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing:
            changed = False
            if not existing.department_id and admin_department:
                existing.department_id = admin_department.id
                changed = True
            if not existing.company_domain and '@' in existing.email:
                existing.company_domain = existing.email.split('@', 1)[1].lower()
                changed = True
            if existing.role != 'master_admin':
                existing.role = 'master_admin'
                changed = True
            for flag in ('allow_helpdesk_admin', 'allow_inventory', 'allow_licenses', 'allow_compliance'):
                if not getattr(existing, flag):
                    setattr(existing, flag, True)
                    changed = True
            if not existing.two_factor_required and not existing.two_factor_enabled:
                existing.two_factor_required = True
                changed = True
            if changed or created:
                db.session.commit()
                click.echo('Existing admin user repaired. Department/domain/access are ready.')
            else:
                click.echo('Admin user already exists and is ready.')
            return

        username = email.split('@', 1)[0].strip().lower()
        if User.query.filter_by(username=username).first():
            username = None

        user = User(
            name=name.strip(),
            first_name=name.strip().split(' ', 1)[0],
            last_name=name.strip().split(' ', 1)[1] if ' ' in name.strip() else '',
            email=email,
            username=username,
            role='master_admin',
            department_id=admin_department.id if admin_department else None,
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

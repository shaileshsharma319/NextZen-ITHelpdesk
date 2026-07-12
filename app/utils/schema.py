from sqlalchemy import inspect, text

from app import db


def ensure_helpdesk_schema():
    inspector = inspect(db.engine)
    if 'users' not in inspector.get_table_names():
        return

    table_names = inspector.get_table_names()
    existing = {column['name'] for column in inspector.get_columns('users')}
    dialect = db.engine.dialect.name

    if dialect == 'mysql':
        columns = {
            'two_factor_required': 'ALTER TABLE users ADD COLUMN two_factor_required TINYINT(1) NOT NULL DEFAULT 0',
            'two_factor_enabled': 'ALTER TABLE users ADD COLUMN two_factor_enabled TINYINT(1) NOT NULL DEFAULT 0',
            'two_factor_secret': 'ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(64) NULL',
            'two_factor_backup_codes': 'ALTER TABLE users ADD COLUMN two_factor_backup_codes TEXT NULL',
            'work_state': 'ALTER TABLE users ADD COLUMN work_state VARCHAR(120) NULL',
            'state_code': 'ALTER TABLE users ADD COLUMN state_code VARCHAR(8) NULL',
            'location_code': 'ALTER TABLE users ADD COLUMN location_code VARCHAR(8) NULL',
        }
    else:
        columns = {
            'two_factor_required': 'ALTER TABLE users ADD COLUMN two_factor_required BOOLEAN NOT NULL DEFAULT 0',
            'two_factor_enabled': 'ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT 0',
            'two_factor_secret': 'ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(64)',
            'two_factor_backup_codes': 'ALTER TABLE users ADD COLUMN two_factor_backup_codes TEXT',
            'work_state': 'ALTER TABLE users ADD COLUMN work_state VARCHAR(120)',
            'state_code': 'ALTER TABLE users ADD COLUMN state_code VARCHAR(8)',
            'location_code': 'ALTER TABLE users ADD COLUMN location_code VARCHAR(8)',
        }

    for column_name, ddl in columns.items():
        if column_name not in existing:
            db.session.execute(text(ddl))

    if 'tickets' in table_names:
        ticket_columns = {column['name']: column for column in inspector.get_columns('tickets')}
        ticket_number = ticket_columns.get('ticket_number')
        ticket_number_length = getattr(ticket_number['type'], 'length', None) if ticket_number else None
        if ticket_number and ticket_number_length and ticket_number_length < 32:
            if dialect == 'mysql':
                db.session.execute(text('ALTER TABLE tickets MODIFY COLUMN ticket_number VARCHAR(32) NULL'))

    db.session.commit()

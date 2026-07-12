from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    cols = [c['name'] for c in inspect(db.engine).get_columns('software')]
    print('Current software columns:', cols)
    if 'license_edition' not in cols:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE software ADD COLUMN license_edition ENUM('msdn','oem_pro','oem_sl','retail','volume','other') NULL"))
            conn.commit()
        print('license_edition column ADDED')
    else:
        print('license_edition already EXISTS')

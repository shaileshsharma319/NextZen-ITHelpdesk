"""Add new employee fields to users table"""
from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    existing = [c['name'] for c in inspector.get_columns('users')]
    print("Existing columns:", existing)

    new_cols = [
        ("employee_id",           "VARCHAR(20)"),
        ("first_name",            "VARCHAR(60)"),
        ("last_name",             "VARCHAR(60)"),
        ("username",              "VARCHAR(60)"),
        ("designation",           "VARCHAR(100)"),
        ("reporting_manager_id",  "INT"),
        ("date_of_joining",       "DATE"),
        ("created_by_id",         "INT"),
    ]

    with db.engine.begin() as conn:
        for col, typedef in new_cols:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typedef}"))
                print(f"  Added: {col}")
            else:
                print(f"  Exists: {col}")

        # Add unique indexes separately (won't error if already exists)
        for col in ("employee_id", "username"):
            if col not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE users ADD UNIQUE INDEX uq_users_{col} ({col})"))
                    print(f"  Unique index: {col}")
                except Exception as e:
                    print(f"  Index skip {col}: {e}")

    print("\nDone! New columns:")
    inspector2 = inspect(db.engine)
    print([c['name'] for c in inspector2.get_columns('users')])

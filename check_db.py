from app import create_app, db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Total tables: {len(tables)}\n")
    for table in sorted(tables):
        cols = inspector.get_columns(table)
        # row count
        count = db.session.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
        print(f"{'='*55}")
        print(f"  TABLE: {table.upper():<30} Rows: {count}")
        print(f"{'='*55}")
        for col in cols:
            nullable = 'NULL' if col['nullable'] else 'NOT NULL'
            default  = f" DEFAULT={col['default']}" if col.get('default') else ''
            print(f"  {col['name']:<28} {str(col['type']):<20} {nullable}{default}")
        print()

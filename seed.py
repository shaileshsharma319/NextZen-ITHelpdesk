"""
Run once to seed the database with initial data.
Usage: python seed.py
"""
from app import create_app, db
from app.models.user import User
from app.models.department import Department
from app.models.asset import Asset

app = create_app()

with app.app_context():
    db.create_all()

    # Departments
    dept_names = [
        ('IT Department', 'Information Technology', 'Floor 1'),
        ('Human Resources', 'HR & People Management', 'Floor 2'),
        ('Finance', 'Finance & Accounting', 'Floor 3'),
        ('Operations', 'Operations & Logistics', 'Floor 4'),
    ]
    depts = {}
    for name, desc, loc in dept_names:
        if not Department.query.filter_by(name=name).first():
            d = Department(name=name, description=desc, location=loc)
            db.session.add(d)
            db.session.flush()
            depts[name] = d
        else:
            depts[name] = Department.query.filter_by(name=name).first()
    db.session.commit()

    # Admin user
    if not User.query.filter_by(email='admin@helpdesk.com').first():
        admin = User(name='Administrator', email='admin@helpdesk.com', role='master_admin',
                     department_id=depts['IT Department'].id)
        admin.set_password('Admin@1234')
        db.session.add(admin)

    # IT Staff
    if not User.query.filter_by(email='staff@helpdesk.com').first():
        staff = User(name='IT Staff', email='staff@helpdesk.com', role='admin_staff',
                     department_id=depts['IT Department'].id)
        staff.set_password('Staff@1234')
        db.session.add(staff)

    # Regular user
    if not User.query.filter_by(email='user@helpdesk.com').first():
        user = User(name='John Employee', email='user@helpdesk.com', role='user',
                    department_id=depts['Human Resources'].id)
        user.set_password('User@1234')
        db.session.add(user)

    db.session.commit()

    # Sample assets
    sample_assets = [
        ('Dell Latitude 5420', 'IT-PC-001', 'computer', 'Dell', 'Latitude 5420', 'SN001', 'in_use'),
        ('HP LaserJet Pro', 'IT-PRN-001', 'printer', 'HP', 'LaserJet Pro M404', 'SN002', 'available'),
        ('Cisco Switch 24-Port', 'IT-NET-001', 'network', 'Cisco', 'SG350-28', 'SN003', 'in_use'),
        ('Dell PowerEdge Server', 'IT-SRV-001', 'server', 'Dell', 'PowerEdge R740', 'SN004', 'in_use'),
        ('LG Monitor 27"', 'IT-MON-001', 'monitor', 'LG', '27UK850', 'SN005', 'available'),
    ]
    it_dept = depts['IT Department']
    for name, tag, atype, brand, model, sn, status in sample_assets:
        if not Asset.query.filter_by(asset_tag=tag).first():
            a = Asset(name=name, asset_tag=tag, asset_type=atype, brand=brand,
                      model=model, serial_number=sn, status=status,
                      department_id=it_dept.id)
            db.session.add(a)

    db.session.commit()
    print('Database seeded successfully!')
    print()
    print('Login Credentials:')
    print('  Admin : admin@helpdesk.com  / Admin@1234')
    print('  Staff : staff@helpdesk.com  / Staff@1234')
    print('  User  : user@helpdesk.com   / User@1234')

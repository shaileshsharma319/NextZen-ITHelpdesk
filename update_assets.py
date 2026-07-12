from app import create_app, db
from app.models.asset import Asset
from app.models.user import User

app = create_app()
with app.app_context():
    staff = User.query.filter_by(email='staff@helpdesk.com').first()
    user  = User.query.filter_by(email='user@helpdesk.com').first()

    data = [
        (1, 'PC-DELL-001',  '192.168.1.101', user.id  if user  else None),
        (2, 'PRN-HP-001',   '192.168.1.102', staff.id if staff else None),
        (3, 'SW-CISCO-001', '192.168.1.1',   None),
        (4, 'SRV-DELL-001', '192.168.1.10',  staff.id if staff else None),
        (5, 'MON-LG-001',   '192.168.1.105', user.id  if user  else None),
    ]

    for asset_id, hostname, ip, uid in data:
        a = Asset.query.get(asset_id)
        if a:
            a.hostname         = hostname
            a.ip_address       = ip
            a.assigned_user_id = uid

    db.session.commit()

    for a in Asset.query.all():
        print(f'{a.name:<25} | {str(a.hostname):<15} | {str(a.ip_address):<15} | {a.assigned_user.name if a.assigned_user else "Unassigned"}')

    print('\nAssets updated successfully!')

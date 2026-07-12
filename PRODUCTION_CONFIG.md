# Production Config Safety

Use `.env` only on the server or local machine. Do not share it and do not commit it.

Use `.env.example` as the safe template for other users or deployments.

## Safe Setup

1. Copy `.env.example` to `.env`.
2. Replace `SECRET_KEY` with a strong random value.
3. Use a dedicated MySQL user, not `root`.
4. Add real SMTP settings only on the machine that sends email.
5. Keep `FLASK_DEBUG=False` for production.

## Generate Secret Key

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Example MySQL App User

Run this in MySQL as root/admin and change the password:

```sql
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
```

Then set:

```env
DATABASE_URL=mysql+pymysql://helpdesk_app:change-this-password@localhost:3306/helpdesk_db
```

## Important

If `.env` is ever shared by mistake, immediately change:

- `SECRET_KEY`
- MySQL password
- Email app password

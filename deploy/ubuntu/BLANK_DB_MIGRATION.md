# Blank Ubuntu Database Migration

Use this process when the Ubuntu server has a fresh/blank MySQL database.

This project does not use a public seed page. Initial setup is done with private terminal commands only.

## 1. Create Blank Database

Login to MySQL:

```bash
sudo mysql
```

Run this SQL. Change the password before production:

```sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 2. Create Production Environment File

```bash
sudo mkdir -p /etc/helpdesk
sudo cp /opt/helpdesk/.env.example /etc/helpdesk/helpdesk.env
sudo nano /etc/helpdesk/helpdesk.env
```

Minimum required values:

```env
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
SECRET_KEY=replace-with-strong-secret
DATABASE_URL=mysql+pymysql://helpdesk_app:change-this-password@localhost:3306/helpdesk_db
```

Generate a strong secret:

```bash
/opt/helpdesk/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Protect the env file:

```bash
sudo chown root:www-data /etc/helpdesk/helpdesk.env
sudo chmod 640 /etc/helpdesk/helpdesk.env
```

## 3. Create Tables And Defaults

The app creates tables automatically when Flask loads.

Run default setup:

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
```

This creates:

- all required database tables
- default departments

It does not create demo tickets, demo users, demo assets, or sample passwords.

## 4. Create First Admin

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-admin
```

It will ask for:

- email
- name
- password

The first admin is created as system admin and MFA is required on first login.

## 5. Verify Database

```bash
sudo mysql
```

```sql
USE helpdesk_db;
SHOW TABLES;
SELECT id, name FROM departments;
SELECT id, name, email, role FROM users;
EXIT;
```

Expected result:

- tables are visible
- departments exist
- one admin user exists

## 6. Start Services

```bash
sudo systemctl start helpdesk
sudo systemctl start helpdesk-email-fetch
```

Check service status:

```bash
sudo systemctl status helpdesk
sudo systemctl status helpdesk-email-fetch
```

## 7. After Git Updates

When pulling new code from Git:

```bash
cd /opt/helpdesk
sudo git pull
sudo /opt/helpdesk/venv/bin/pip install -r requirements.txt
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
sudo systemctl restart helpdesk
sudo systemctl restart helpdesk-email-fetch
```

`init-defaults` is safe to run again. It will not duplicate departments.

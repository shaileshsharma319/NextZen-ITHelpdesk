# Ubuntu Fresh Install

Use this guide on a new Ubuntu 22.04/24.04 server.

The errors below mean the project was not cloned yet:

```text
cp: cannot stat '/opt/helpdesk/.env.example': No such file or directory
/opt/helpdesk/venv/bin/python: No such file or directory
```

Fix: start from step 1. Do not skip the clone and virtual environment steps.

## 1. Install Base Packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip mysql-server nginx
```

## 2. Clone Project

```bash
sudo rm -rf /opt/helpdesk
sudo git clone https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git /opt/helpdesk
cd /opt/helpdesk
```

Verify:

```bash
ls -la /opt/helpdesk/.env.example
ls -la /opt/helpdesk/requirements.txt
```

Both files must be visible before continuing.

## 3. Create Python Virtual Environment

```bash
sudo python3 -m venv /opt/helpdesk/venv
sudo /opt/helpdesk/venv/bin/pip install --upgrade pip
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
```

Verify:

```bash
/opt/helpdesk/venv/bin/python --version
```

## 4. Start MySQL

```bash
sudo systemctl enable mysql
sudo systemctl start mysql
sudo systemctl status mysql
```

Status should show:

```text
active (running)
```

## 5. Create Database And App User

Open MySQL:

```bash
sudo mysql
```

Run this SQL. Change `change-this-password` to your real strong DB password:

```sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Test login:

```bash
mysql -u helpdesk_app -p helpdesk_db
```

Then:

```sql
SELECT DATABASE();
EXIT;
```

## 6. Create Production Env File

```bash
sudo mkdir -p /etc/helpdesk
sudo cp /opt/helpdesk/.env.example /etc/helpdesk/helpdesk.env
sudo nano /etc/helpdesk/helpdesk.env
```

Set these important values:

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

Replace `SECRET_KEY` with the generated value.

Protect env file:

```bash
sudo chown root:www-data /etc/helpdesk/helpdesk.env
sudo chmod 640 /etc/helpdesk/helpdesk.env
```

## 7. Prepare Upload Folder

```bash
sudo mkdir -p /opt/helpdesk/app/static/uploads
sudo chown -R www-data:www-data /opt/helpdesk/app/static/uploads
```

## 8. Create Tables And Default Departments

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
```

This creates all tables and default departments.

## 9. Create First Admin

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-admin
```

Enter admin email, name, and password.

## 10. Install Services

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk.service /etc/systemd/system/helpdesk.service
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk-email-fetch.service /etc/systemd/system/helpdesk-email-fetch.service
sudo systemctl daemon-reload
sudo systemctl enable helpdesk
sudo systemctl enable helpdesk-email-fetch
sudo systemctl start helpdesk
sudo systemctl start helpdesk-email-fetch
```

Check:

```bash
sudo systemctl status helpdesk
sudo systemctl status helpdesk-email-fetch
```

## 11. Test Locally On Server

```bash
curl -I http://127.0.0.1:5000
```

Expected:

```text
HTTP/1.1 302 FOUND
```

or:

```text
HTTP/1.1 200 OK
```

## 12. Nginx And Domain

Edit:

```bash
sudo nano /opt/helpdesk/deploy/ubuntu/nginx-helpdesk.conf
```

Change:

```nginx
server_name helpdesk.example.com;
```

Install Nginx site:

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/nginx-helpdesk.conf /etc/nginx/sites-available/helpdesk
sudo ln -sf /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
sudo nginx -t
sudo systemctl reload nginx
```

## 13. Common Fixes

If `.env.example` is missing:

```bash
ls -la /opt/helpdesk
```

If `/opt/helpdesk/venv/bin/python` is missing:

```bash
sudo python3 -m venv /opt/helpdesk/venv
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
```

If database login fails:

```bash
sudo mysql
```

```sql
ALTER USER 'helpdesk_app'@'localhost' IDENTIFIED BY 'new-strong-password';
FLUSH PRIVILEGES;
EXIT;
```

Then update:

```bash
sudo nano /etc/helpdesk/helpdesk.env
```

Restart:

```bash
sudo systemctl restart helpdesk helpdesk-email-fetch
```

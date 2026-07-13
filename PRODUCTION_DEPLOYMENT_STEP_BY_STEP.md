# Production Deployment Step By Step

Use this single guide for a fresh Ubuntu server.

Project path:

```text
/opt/helpdesk
```

Service user:

```text
www-data
```

Database:

```text
helpdesk_db
```

Database user:

```text
helpdesk_app
```

## Step 1. Prerequisites Install

Update Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
```

Install required packages:

```bash
sudo apt install -y git python3 python3-venv python3-pip mysql-server nginx curl
```

Check versions:

```bash
python3 --version
mysql --version
nginx -v
git --version
```

If Git is missing:

```text
sudo: git: command not found
```

Install Git before folder creation or clone:

```bash
sudo apt update
sudo apt install -y git
git --version
```

## Step 2. MySQL Install And Full Configuration

Start MySQL:

```bash
sudo systemctl enable mysql
sudo systemctl start mysql
sudo systemctl status mysql
```

Expected:

```text
active (running)
```

Secure MySQL:

```bash
sudo mysql_secure_installation
```

Recommended answers:

```text
VALIDATE PASSWORD COMPONENT: Y
Password strength: 2
Remove anonymous users: Y
Disallow root login remotely: Y
Remove test database: Y
Reload privilege tables: Y
```

Open MySQL:

```bash
sudo mysql
```

Create database and app user. Change `change-this-password` before production:

```sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Test app DB login:

```bash
mysql -u helpdesk_app -p helpdesk_db
```

Run:

```sql
SELECT DATABASE();
EXIT;
```

Expected:

```text
helpdesk_db
```

## Step 3. Folder Creation And Permissions

Before creating folders, confirm Git is available:

```bash
git --version
```

If this fails, run:

```bash
sudo apt update
sudo apt install -y git
```

Create project folder:

```bash
sudo mkdir -p /opt/helpdesk
sudo chown -R $USER:$USER /opt/helpdesk
```

Create environment config folder:

```bash
sudo mkdir -p /etc/helpdesk
```

Create upload folder:

```bash
sudo mkdir -p /opt/helpdesk/app/static/uploads
sudo chown -R www-data:www-data /opt/helpdesk/app/static/uploads
```

## Step 4. Git Clone Project

If `/opt/helpdesk` is empty:

```bash
sudo rm -rf /opt/helpdesk
sudo git clone https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git /opt/helpdesk
cd /opt/helpdesk
```

Verify required files:

```bash
ls -la /opt/helpdesk/.env.example
ls -la /opt/helpdesk/requirements.txt
ls -la /opt/helpdesk/wsgi.py
```

If any file is missing, stop and fix Git clone first.

## Step 5. Python Virtual Environment

Create venv:

```bash
sudo python3 -m venv /opt/helpdesk/venv
```

Install Python packages:

```bash
sudo /opt/helpdesk/venv/bin/pip install --upgrade pip
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
```

Verify:

```bash
/opt/helpdesk/venv/bin/python --version
/opt/helpdesk/venv/bin/python -m flask --version
```

## Step 6. Production Environment File

Copy template:

```bash
sudo cp /opt/helpdesk/.env.example /etc/helpdesk/helpdesk.env
```

Generate strong secret:

```bash
/opt/helpdesk/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit env:

```bash
sudo nano /etc/helpdesk/helpdesk.env
```

Minimum production values:

```env
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
SECRET_KEY=paste-generated-secret-here
DATABASE_URL=mysql+pymysql://helpdesk_app:change-this-password@localhost:3306/helpdesk_db
```

Optional mail values:

```env
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=helpdesk@yourcompany.com
MAIL_PASSWORD=mail-app-password
MAIL_DEFAULT_SENDER=helpdesk@yourcompany.com
EMAIL_AUTO_FETCH_ENABLED=True
EMAIL_AUTO_FETCH_INTERVAL_SECONDS=600
```

Protect env file:

```bash
sudo chown root:www-data /etc/helpdesk/helpdesk.env
sudo chmod 640 /etc/helpdesk/helpdesk.env
```

## Step 7. Database Table Creation

The app creates all tables when Flask loads.

Run default setup:

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
```

This creates:

- all database tables
- default departments

It does not create demo tickets, demo users, demo assets, or sample passwords.

Verify tables:

```bash
sudo mysql
```

```sql
USE helpdesk_db;
SHOW TABLES;
SELECT id, name FROM departments;
EXIT;
```

## Step 8. Create First Admin

Run:

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-admin
```

Enter:

```text
Email
Name
Password
Confirm password
```

Verify user:

```bash
sudo mysql
```

```sql
USE helpdesk_db;
SELECT id, name, email, role FROM users;
EXIT;
```

The first admin must set up MFA on first login.

## Step 9. Install And Start Services

Copy service files:

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk.service /etc/systemd/system/helpdesk.service
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk-email-fetch.service /etc/systemd/system/helpdesk-email-fetch.service
```

Enable and start:

```bash
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

View logs:

```bash
sudo journalctl -u helpdesk -f
sudo journalctl -u helpdesk-email-fetch -f
```

## Step 10. Local App Test

Test from server:

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

## Step 11. Nginx Reverse Proxy

Edit Nginx config:

```bash
sudo nano /opt/helpdesk/deploy/ubuntu/nginx-helpdesk.conf
```

Change:

```nginx
server_name helpdesk.example.com;
```

to your real domain.

Install site:

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/nginx-helpdesk.conf /etc/nginx/sites-available/helpdesk
sudo ln -sf /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
sudo nginx -t
sudo systemctl reload nginx
```

## Step 12. HTTPS SSL

After DNS points to the server:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d helpdesk.example.com
```

Replace `helpdesk.example.com` with your domain.

## Step 13. Update From Git

When new code is pushed:

```bash
cd /opt/helpdesk
sudo git pull
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
sudo systemctl restart helpdesk
sudo systemctl restart helpdesk-email-fetch
```

## Step 14. Common Errors

Error:

```text
sudo: git: command not found
bash: cd: /opt/helpdesk: No such file or directory
```

Reason:

```text
Git is not installed, so clone failed. Because clone failed, /opt/helpdesk was not created.
```

Fix:

```bash
sudo apt update
sudo apt install -y git
git --version
sudo rm -rf /opt/helpdesk
sudo git clone https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git /opt/helpdesk
cd /opt/helpdesk
```

Error:

```text
cp: cannot stat '/opt/helpdesk/.env.example': No such file or directory
```

Fix:

```bash
sudo git clone https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git /opt/helpdesk
ls -la /opt/helpdesk/.env.example
```

Error:

```text
/opt/helpdesk/venv/bin/python: No such file or directory
```

Fix:

```bash
sudo python3 -m venv /opt/helpdesk/venv
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
```

Error:

```text
Access denied for user 'helpdesk_app'@'localhost'
```

Fix:

```bash
sudo mysql
```

```sql
ALTER USER 'helpdesk_app'@'localhost' IDENTIFIED BY 'new-strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Then update:

```bash
sudo nano /etc/helpdesk/helpdesk.env
sudo systemctl restart helpdesk helpdesk-email-fetch
```

Error:

```text
502 Bad Gateway
```

Check app service:

```bash
sudo systemctl status helpdesk
sudo journalctl -u helpdesk -n 100
```

# Ubuntu Hosting Guide

This project can run on Ubuntu with:

- MySQL
- Gunicorn
- Nginx
- systemd services

Recommended server path:

```bash
/opt/helpdesk
```

## 1. Install Server Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server nginx
```

## 2. Clone Project From Git

Replace the Git URL with your real repository URL:

```bash
sudo git clone https://github.com/YOUR-USER/YOUR-REPO.git /opt/helpdesk
cd /opt/helpdesk
```

## 3. Create Python Environment

```bash
sudo python3 -m venv /opt/helpdesk/venv
sudo /opt/helpdesk/venv/bin/pip install --upgrade pip
sudo /opt/helpdesk/venv/bin/pip install -r /opt/helpdesk/requirements.txt
```

## 4. Create MySQL Database And User

Login to MySQL:

```bash
sudo mysql
```

Run this SQL. Change the password:

```sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 5. Create Production Env File

```bash
sudo mkdir -p /etc/helpdesk
sudo cp /opt/helpdesk/.env.example /etc/helpdesk/helpdesk.env
sudo nano /etc/helpdesk/helpdesk.env
```

Set these values:

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

## 6. Prepare Upload Folders

```bash
sudo mkdir -p /opt/helpdesk/app/static/uploads
sudo chown -R www-data:www-data /opt/helpdesk/app/static/uploads
```

## 7. Create Default Records

This project does not need a public seed page. Use private server commands only.

Create default departments:

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
```

Create the first admin user:

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-admin
```

The first admin will be required to set up MFA on first login.

## 8. Install systemd Services

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk.service /etc/systemd/system/helpdesk.service
sudo cp /opt/helpdesk/deploy/ubuntu/helpdesk-email-fetch.service /etc/systemd/system/helpdesk-email-fetch.service
sudo systemctl daemon-reload
sudo systemctl enable helpdesk
sudo systemctl enable helpdesk-email-fetch
sudo systemctl start helpdesk
sudo systemctl start helpdesk-email-fetch
```

Check status:

```bash
sudo systemctl status helpdesk
sudo systemctl status helpdesk-email-fetch
```

## 9. Configure Nginx

Edit `deploy/ubuntu/nginx-helpdesk.conf` and change:

```nginx
server_name helpdesk.example.com;
```

Then install it:

```bash
sudo cp /opt/helpdesk/deploy/ubuntu/nginx-helpdesk.conf /etc/nginx/sites-available/helpdesk
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
sudo nginx -t
sudo systemctl reload nginx
```

## 10. Enable HTTPS

After your domain DNS points to the server:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d helpdesk.example.com
```

## Common Commands

Restart web app:

```bash
sudo systemctl restart helpdesk
```

Restart email fetch:

```bash
sudo systemctl restart helpdesk-email-fetch
```

View logs:

```bash
sudo journalctl -u helpdesk -f
sudo journalctl -u helpdesk-email-fetch -f
```

Update from Git:

```bash
cd /opt/helpdesk
sudo git pull
sudo /opt/helpdesk/venv/bin/pip install -r requirements.txt
sudo systemctl restart helpdesk
sudo systemctl restart helpdesk-email-fetch
```

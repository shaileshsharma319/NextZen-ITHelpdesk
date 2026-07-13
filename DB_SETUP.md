# Database Setup

Use this guide to create a fresh MySQL database for the Helpdesk project on Ubuntu.

## 1. Install MySQL

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql
sudo systemctl status mysql
```

Expected status:

```text
active (running)
```

## 2. Secure MySQL

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

## 3. Create Database And App User

Login:

```bash
sudo mysql
```

Run SQL:

```sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_app'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON helpdesk_db.* TO 'helpdesk_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Use a strong password instead of `change-this-password`.

## 4. Test Database Login

```bash
mysql -u helpdesk_app -p helpdesk_db
```

Then:

```sql
SELECT DATABASE();
EXIT;
```

Expected result:

```text
helpdesk_db
```

## 5. Configure Helpdesk Env

Create env file:

```bash
sudo mkdir -p /etc/helpdesk
sudo cp /opt/helpdesk/.env.example /etc/helpdesk/helpdesk.env
sudo nano /etc/helpdesk/helpdesk.env
```

Set:

```env
DATABASE_URL=mysql+pymysql://helpdesk_app:change-this-password@localhost:3306/helpdesk_db
```

Also set a strong `SECRET_KEY`.

Protect file:

```bash
sudo chown root:www-data /etc/helpdesk/helpdesk.env
sudo chmod 640 /etc/helpdesk/helpdesk.env
```

## 6. Create Tables And Default Departments

The Flask app creates tables when it loads.

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-defaults
```

This creates:

- all tables
- default departments

It does not create demo users, demo tickets, or sample passwords.

## 7. Create First Admin

```bash
cd /opt/helpdesk
sudo -u www-data /opt/helpdesk/venv/bin/flask --app wsgi:app init-admin
```

The admin will be required to set up MFA on first login.

## 8. Verify Tables

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

Expected:

- tables are visible
- departments exist
- first admin user exists

# NextZen IT HelpDesk - Windows Hosting Step By Step

Use this guide to host the HelpDesk application on Windows Server or a Windows 10/11 machine.

Recommended production setup on Windows:

- Python 3.11 or 3.12
- MySQL 8.4
- Waitress WSGI server
- NSSM Windows service manager
- Optional IIS reverse proxy for domain/SSL

## Step 1. Install Required Software

Open PowerShell as Administrator.

### 1.1 Install Git

```powershell
winget install Git.Git
```

Close PowerShell and open it again, then verify:

```powershell
git --version
```

### 1.2 Install Python

```powershell
winget install Python.Python.3.12
```

Close PowerShell and open it again, then verify:

```powershell
python --version
pip --version
```

### 1.3 Install MySQL

```powershell
winget install Oracle.MySQL
```

If the `mysql` command is not available, use this path:

```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
```

Start MySQL service:

```powershell
net start MySQL84
```

If service name is different, check:

```powershell
Get-Service *mysql*
```

## Step 2. Create MySQL Database

Open PowerShell as Administrator:

```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u root -p
```

Inside MySQL, run:

```sql
CREATE DATABASE helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'helpdesk_app'@'localhost' IDENTIFIED BY 'CHANGE_STRONG_PASSWORD';

GRANT ALL PRIVILEGES ON helpdesk_db.* TO 'helpdesk_app'@'localhost';

FLUSH PRIVILEGES;

EXIT;
```

Replace `CHANGE_STRONG_PASSWORD` with a strong password.

## Step 3. Create Application Folder

```powershell
mkdir "C:\HelpDesk"
mkdir "C:\HelpDesk\uploads"
```

## Step 4. Clone Project From GitHub

```powershell
cd "C:\HelpDesk"
git clone https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git app
cd "C:\HelpDesk\app"
```

## Step 5. Create Python Virtual Environment

```powershell
python -m venv "C:\HelpDesk\venv"
"C:\HelpDesk\venv\Scripts\python.exe" -m pip install --upgrade pip
"C:\HelpDesk\venv\Scripts\pip.exe" install -r "C:\HelpDesk\app\requirements.txt"
```

## Step 6. Create `.env` File

Copy example file:

```powershell
copy "C:\HelpDesk\app\.env.example" "C:\HelpDesk\app\.env"
notepad "C:\HelpDesk\app\.env"
```

Use this Windows production example:

```env
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

SECRET_KEY=replace-with-generated-secret

DATABASE_URL=mysql+pymysql://helpdesk_app:CHANGE_STRONG_PASSWORD@localhost:3306/helpdesk_db
UPLOAD_FOLDER=C:\HelpDesk\uploads

MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=helpdesk@yourcompany.com
MAIL_PASSWORD=replace-mail-password
MAIL_DEFAULT_SENDER=helpdesk@yourcompany.com

EMAIL_AUTO_FETCH_ENABLED=True
EMAIL_AUTO_FETCH_INTERVAL_SECONDS=600
```

Generate secret key:

```powershell
"C:\HelpDesk\venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste that value into `SECRET_KEY`.

## Step 7. Create Tables And Default Data

```powershell
cd "C:\HelpDesk\app"
"C:\HelpDesk\venv\Scripts\flask.exe" --app wsgi:app init-defaults
"C:\HelpDesk\venv\Scripts\flask.exe" --app wsgi:app init-admin
```

This creates missing tables, default departments, default admin, permissions, categories, and required system data.

## Step 8. Test Run Manually

```powershell
cd "C:\HelpDesk\app"
"C:\HelpDesk\venv\Scripts\waitress-serve.exe" --host=127.0.0.1 --port=5000 wsgi:app
```

Open:

```text
http://127.0.0.1:5000
```

Default admin is created by `init-admin`. If your project prints login details, use those. Otherwise check your configured admin in the database/user setup.

Stop the test server with:

```text
Ctrl + C
```

## Step 9. Run As Windows Service

Use NSSM to run the app in the background.

### 9.1 Install NSSM

```powershell
winget install NSSM.NSSM
```

If winget cannot find NSSM, download from:

```text
https://nssm.cc/download
```

### 9.2 Create HelpDesk Service

Open PowerShell as Administrator:

```powershell
nssm install HelpDeskApp
```

In the NSSM window:

```text
Application path:
C:\HelpDesk\venv\Scripts\waitress-serve.exe

Startup directory:
C:\HelpDesk\app

Arguments:
--host=127.0.0.1 --port=5000 wsgi:app
```

Go to `I/O` tab and set:

```text
Output:
C:\HelpDesk\helpdesk-service.log

Error:
C:\HelpDesk\helpdesk-service-error.log
```

Click `Install service`.

Start service:

```powershell
net start HelpDeskApp
```

Check:

```powershell
Get-Service HelpDeskApp
```

## Step 10. Optional Email Fetch Service

If your app has a background email fetch command/script, create a second NSSM service only after confirming the command works manually.

Manual check example:

```powershell
cd "C:\HelpDesk\app"
"C:\HelpDesk\venv\Scripts\flask.exe" --app wsgi:app fetch-email
```

If your project does not expose `fetch-email`, use the built-in app email fetch configuration page instead.

## Step 11. Allow LAN Access

If other computers need to open the HelpDesk portal, change Waitress host from:

```text
127.0.0.1
```

to:

```text
0.0.0.0
```

Then allow port 5000:

```powershell
New-NetFirewallRule -DisplayName "HelpDesk App 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

Users can open:

```text
http://SERVER-IP:5000
```

## Step 12. Optional IIS Reverse Proxy

For production domain and SSL, keep Waitress on `127.0.0.1:5000` and put IIS in front.

Install IIS:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole,IIS-WebServer,IIS-ManagementConsole -All
```

Install:

- IIS URL Rewrite
- IIS Application Request Routing

Then create reverse proxy:

```text
https://helpdesk.yourcompany.com -> http://127.0.0.1:5000
```

Use IIS for SSL certificate binding.

## Step 13. Update Application From Git

When new code is pushed to GitHub:

```powershell
cd "C:\HelpDesk\app"
git pull
"C:\HelpDesk\venv\Scripts\pip.exe" install -r "C:\HelpDesk\app\requirements.txt"
"C:\HelpDesk\venv\Scripts\flask.exe" --app wsgi:app init-defaults
Restart-Service HelpDeskApp
```

If admin/default repair is needed:

```powershell
"C:\HelpDesk\venv\Scripts\flask.exe" --app wsgi:app init-admin
Restart-Service HelpDeskApp
```

## Step 14. Common Errors

### `git is not recognized`

Install Git and reopen PowerShell:

```powershell
winget install Git.Git
```

### `mysql is not recognized`

Use full MySQL bin path:

```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u root -p
```

### Cannot connect to MySQL

Check service:

```powershell
Get-Service *mysql*
net start MySQL84
```

### Upload permission issue

Make sure this folder exists:

```powershell
mkdir "C:\HelpDesk\uploads"
```

Make sure `.env` has:

```env
UPLOAD_FOLDER=C:\HelpDesk\uploads
```

Restart:

```powershell
Restart-Service HelpDeskApp
```

### Page still showing old design

Restart service and hard refresh browser:

```powershell
Restart-Service HelpDeskApp
```

Then press:

```text
Ctrl + F5
```

## Step 15. Quick Daily Commands

Start:

```powershell
net start HelpDeskApp
```

Stop:

```powershell
net stop HelpDeskApp
```

Restart:

```powershell
Restart-Service HelpDeskApp
```

View logs:

```powershell
notepad "C:\HelpDesk\helpdesk-service.log"
notepad "C:\HelpDesk\helpdesk-service-error.log"
```


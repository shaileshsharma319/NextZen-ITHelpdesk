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

## Step 12. Host With IIS Reverse Proxy

IIS should work as the public front door. Flask should still run behind IIS using Waitress.

Recommended flow:

```text
User Browser
  -> IIS website on 80/443
  -> Reverse proxy to Waitress
  -> http://127.0.0.1:5000
  -> Flask HelpDesk app
  -> MySQL
```

Keep Waitress private:

```text
127.0.0.1:5000
```

Use IIS for:

- domain name
- SSL certificate
- public port 80/443
- reverse proxy
- Windows hosting management

### 12.1 Install IIS

Open PowerShell as Administrator:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole,IIS-WebServer,IIS-ManagementConsole,IIS-HttpRedirect,IIS-StaticContent,IIS-DefaultDocument -All
```

Open IIS Manager:

```powershell
inetmgr
```

### 12.2 Install IIS URL Rewrite And ARR

Download and install these two Microsoft IIS modules:

```text
IIS URL Rewrite
https://www.iis.net/downloads/microsoft/url-rewrite

IIS Application Request Routing ARR
https://www.iis.net/downloads/microsoft/application-request-routing
```

After install, reopen IIS Manager.

### 12.3 Enable ARR Proxy

In IIS Manager:

```text
Server Name
  -> Application Request Routing Cache
  -> Server Proxy Settings
  -> Enable proxy
  -> Apply
```

Important setting:

```text
Enable proxy: Checked
```

Optional but recommended:

```text
Reverse rewrite host in response headers: Checked
```

### 12.4 Create IIS Website

Create folder:

```powershell
mkdir "C:\HelpDesk\iis-root"
```

In IIS Manager:

```text
Sites
  -> Add Website
```

Use:

```text
Site name:
NextZen HelpDesk

Physical path:
C:\HelpDesk\iis-root

Binding type:
http

IP address:
All Unassigned

Port:
80

Host name:
helpdesk.yourcompany.com
```

If you do not have a domain yet, leave Host name blank and use server IP.

### 12.5 Add Reverse Proxy Rule

In IIS Manager:

```text
NextZen HelpDesk site
  -> URL Rewrite
  -> Add Rule(s)
  -> Reverse Proxy
```

Inbound rule target:

```text
127.0.0.1:5000
```

Click OK / Apply.

This creates a rule like:

```text
http://helpdesk.yourcompany.com/* -> http://127.0.0.1:5000/*
```

### 12.6 Confirm Waitress Service Is Running

```powershell
Get-Service HelpDeskApp
Restart-Service HelpDeskApp
```

Test local backend:

```text
http://127.0.0.1:5000
```

Test IIS front URL:

```text
http://helpdesk.yourcompany.com
```

or:

```text
http://SERVER-IP
```

### 12.7 Add Firewall Rule For IIS

Allow HTTP:

```powershell
New-NetFirewallRule -DisplayName "HelpDesk IIS HTTP 80" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

Allow HTTPS if SSL is used:

```powershell
New-NetFirewallRule -DisplayName "HelpDesk IIS HTTPS 443" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

If using IIS reverse proxy, you do not need to open port 5000 to the network. Keep Waitress on `127.0.0.1`.

### 12.8 Add SSL Certificate

In IIS Manager:

```text
Server Name
  -> Server Certificates
  -> Import / Create Certificate
```

Then bind SSL:

```text
NextZen HelpDesk site
  -> Bindings
  -> Add
```

Use:

```text
Type:
https

Port:
443

Host name:
helpdesk.yourcompany.com

SSL certificate:
Select certificate
```

### 12.9 Force HTTP To HTTPS

In IIS URL Rewrite, add HTTP to HTTPS redirect rule:

```text
URL Rewrite
  -> Add Rule(s)
  -> Blank rule
```

Use:

```text
Name:
Redirect HTTP to HTTPS

Pattern:
(.*)

Condition:
{HTTPS} = off

Action type:
Redirect

Redirect URL:
https://{HTTP_HOST}/{R:1}

Redirect type:
Permanent (301)
```

### 12.10 IIS Troubleshooting

If IIS shows `502 Bad Gateway`:

```powershell
Restart-Service HelpDeskApp
```

Then confirm backend:

```text
http://127.0.0.1:5000
```

If backend does not open, check service logs:

```powershell
notepad "C:\HelpDesk\helpdesk-service-error.log"
```

If CSS/icons do not load:

```text
IIS URL Rewrite rule must proxy all paths, including /static/*
```

If login works on `127.0.0.1:5000` but not on IIS domain:

```text
Check SECRET_KEY is fixed in .env.
Do not regenerate SECRET_KEY after users start logging in.
Restart HelpDeskApp after .env changes.
```

If large uploads fail through IIS:

```text
Increase IIS request limit:
IIS Manager -> NextZen HelpDesk -> Request Filtering -> Edit Feature Settings -> Maximum allowed content length
```

For 21 MB upload support, set at least:

```text
30000000
```

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

# Ubuntu Deployment Files

Use the single complete deployment guide:

[../../PRODUCTION_DEPLOYMENT_STEP_BY_STEP.md](../../PRODUCTION_DEPLOYMENT_STEP_BY_STEP.md)

This folder contains production support files used by that guide:

- `gunicorn.conf.py` - Gunicorn web server config
- `helpdesk.service` - systemd service for the Flask web app
- `helpdesk-email-fetch.service` - systemd service for background email ticket fetch
- `nginx-helpdesk.conf` - Nginx reverse proxy config
- `install.sh` - optional helper installer

Do not use old seed files or public seed pages in production.

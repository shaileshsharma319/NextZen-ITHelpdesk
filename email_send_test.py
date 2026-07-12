from app import create_app
app = create_app()
with app.app_context():
    from app.models.email_config import EmailConfig
    from app.utils.email import _apply_config
    from app import mail
    from flask_mail import Message
    cfg = EmailConfig.get()
    print('server:', cfg.mail_server)
    print('port:', cfg.mail_port)
    print('tls:', cfg.mail_use_tls)
    print('ssl:', cfg.mail_use_ssl)
    print('username:', cfg.mail_username)
    _apply_config(cfg)
    try:
        msg = Message(
            subject='IT HelpDesk Test',
            recipients=['shaileshs@winsoftech.in'],
            sender=(cfg.mail_from_name, cfg.mail_from),
            body='Test email from IT HelpDesk.'
        )
        mail.send(msg)
        print('SENT OK')
    except Exception as e:
        print('ERROR:', type(e).__name__, '|', e)

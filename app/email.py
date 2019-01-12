from app import mail
from flask_mail import Message
from threading import Thread
from flask import current_app


def send_email(subject,sender,recipients,text,html, attachments=None, sync=False):
    # sync 同步默认false
    msg = Message(subject=subject,recipients=recipients,sender=sender,body=text,html=html)
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(target=send_emdail_async,args=(current_app._get_current_object(), msg)).start()

def send_emdail_async(app, msg):
    with app.app_context():
        mail.send(msg)
        
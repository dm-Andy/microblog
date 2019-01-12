from app.email import send_email
from flask import render_template,current_app
from flask_babel import _


def send_reset_password_email(user):
    token = user.get_reset_password_token()
    send_email(_('[microblog] 重置密码'),
                sender=current_app.config['ADMINS'][0],
                recipients=[user.email],
                text=render_template('email/reset_password.txt',user=user, token=token),
                html=render_template('email/reset_password.html',user=user, token=token))
                
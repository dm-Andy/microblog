from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm, ResetPasswordRequestForm, ResetPasswordForm
from app.models import User
from flask import render_template,flash,redirect,url_for,request
from app import db
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse
from flask_babel import _
from app.auth.email import send_reset_password_email


@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 判断当前用户是否通过了验证
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_('用户名或密码错误'))
            return redirect(url_for('auth.login'))

        login_user(user, form.remember_me.data)

        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html', title=_('登录'), form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('注册成功'))
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', title=_('注册'), form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        redirect(url_for('main.index'))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_password_email(user)
        # 这里没有提示用户邮箱未注册，所以用户不能从这里得知某个邮箱是否已经注册
        flash(_('发送邮件成功，请检查你的邮箱'))
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html', title=_('重置密码'), form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = User.verify_reset_password_token(token)
    if not user:
        # token验证未通过
        return redirect(url_for('main.index'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('密码重置成功'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', title=_('重置密码'), form=form)

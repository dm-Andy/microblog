from flask_wtf import FlaskForm
from wtforms import StringField,BooleanField,PasswordField,SubmitField
from wtforms.validators import DataRequired,EqualTo,Email,ValidationError
from app.models import User
from flask_babel import _,lazy_gettext as _l


class LoginForm(FlaskForm):
    username = StringField(_l('用户名'), validators=[DataRequired(message=_l('请输入用户名'))])
    password = PasswordField(_l('密码'), validators=[DataRequired(message=_l('请输入密码'))])
    remember_me = BooleanField(_l('记住我'), default=False)
    submit = SubmitField(_l('登录'))

class RegisterForm(FlaskForm):
    username = StringField(_('用户名'), validators=[DataRequired()])
    email = StringField(_l('邮箱'), validators=[DataRequired(),Email()])
    password = PasswordField(_l('密码'), validators=[DataRequired()])
    eq_pwd = PasswordField(_l('重复密码'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('注册'))

    def validate_username(self, username):
        # 检查用户名是否存在
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(_('用户已存在'))
        
    def validate_email(self, email):
        # 检查用户名是否存在
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(_('该邮箱已注册'))
    
class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('邮箱'), validators=[DataRequired(),Email()])
    submit = SubmitField(_l('发送重置邮件'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('密码'), validators=[DataRequired()])
    eq_pwd = PasswordField(_l('重复密码'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('重置密码'))
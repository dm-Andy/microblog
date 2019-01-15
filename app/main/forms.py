from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import User
from flask_babel import _, lazy_gettext as _l
from flask import request


class PostForm(FlaskForm):
    post = TextAreaField(_l('内容'), validators=[
                         DataRequired(_l('内容不能为空')), Length(1, 140)])
    submit = SubmitField(_l('保存'))


class EditProfileForm(FlaskForm):
    username = StringField(_l('用户名'), validators=[DataRequired(_l('请输入用户名'))])
    about_me = TextAreaField(_l('关于我'), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('保存'))

    def __init__(self, original_username, **kwargs):
        super().__init__(**kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username.data).first()
            if user is not None:
                raise ValidationError(_('用户名已存在'))


class SearchForm(FlaskForm):
    q = StringField(_('搜索'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            # 这里为了在routes中验证字段
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super().__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField(_l('信息'), validators=[DataRequired(),Length(0,140)])
    submit = SubmitField(_l('发送'))
# 常用命令
# python -m smtpd -n -c DebuggingServer localhost:8025 开启邮件调试服务器
# pybabel extract -F babel.cfg -k _l -o messages.pot .  提取要翻译的文本
# pybabel init -i messages.pot -d app/translations -l es   生成语言目录
# pybabel compile -d app/translations  编译翻译数据
# 更新翻译
# pybabel extract -F babel.cfg -k _l -o messages.pot .  提取
# pybabel update -i messages.pot -d app/translations   更新

import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 分页每页数量
    POSTS_PER_PAGE = 5

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    # mail 如果启用邮件发送 则export MAIL_SERVER=xxx 否则视为不启用
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT') or 25
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    ADMINS = ['635885852@qq.com']
    # 以下是gmail的配置，需要在账号中设置允许程序访问
    # export MAIL_SERVER=smtp.googlemail.com
    # export MAIL_PORT=587
    # export MAIL_USE_TLS=1
    # export MAIL_USERNAME=<your-gmail-username>
    # export MAIL_PASSWORD=<your-gmail-password>
    DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'
    LANGUAGES = ['en', 'zh_CN']

    YOUDAO_APP_KEY = os.environ.get('YOUDAO_APP_KEY')
    YOUDAO_APP_SECRET_KEY = os.environ.get('YOUDAO_APP_SECRET_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    # 常量
    UNREAD_MESSAGE_COUNT = 'unread_message_count'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

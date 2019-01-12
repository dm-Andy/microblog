import json
import requests
from flask_babel import _
from flask import current_app
from hashlib import md5


def translate(text, source_language, dest_language):
    if not current_app.config['YOUDAO_APP_KEY'] or not current_app.config['YOUDAO_APP_SECRET_KEY']:
        return _('错误：翻译服务未配置'), None

    tmp_sign = current_app.config['YOUDAO_APP_KEY'] + text + \
        current_app.config['SECRET_KEY'] + current_app.config['YOUDAO_APP_SECRET_KEY']
    sign = md5(tmp_sign.encode('utf-8')).hexdigest()

    res = requests.get('http://openapi.youdao.com/api?q={}&from={}&to={}&appKey={}&salt={}&sign={}'.format(
        text, source_language, dest_language, current_app.config['YOUDAO_APP_KEY'], current_app.config['SECRET_KEY'], sign))

    if res.status_code != 200:
        return _('错误：翻译服务返回错误'), None
    data = json.loads(res.content.decode('utf-8'))
    try:
        return data['translation'][0], data['speakUrl']
    except:
        return _('错误：翻译服务返回错误'), None

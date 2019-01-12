from app import create_app, db, cli
from app.models import User, Post

# 配置flask sell 同时也是FLASK_APP的入口
app = create_app()
cli.register(app)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

from app import db, login
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5
import jwt
from time import time
from flask import current_app
from app.search import add_to_index, remove_from_index, query_index


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class SearchableMixin(object):
    '''
    写好search.py后，需要在添加修改和删除的时候更新对应的索引，这里用数据库的接口实现
    查询返回的是ids，需要返回对应的Model
    '''
    @classmethod
    def search(cls, query, page, per_page):
        ids, total = query_index(cls.__tablename__, query, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for x in session._changes['add']:
            if isinstance(x, SearchableMixin):
                add_to_index(x.__tablename__, x)

        for x in session._changes['update']:
            if isinstance(x, SearchableMixin):
                add_to_index(x.__tablename__, x)

        for x in session._changes['delete']:
            if isinstance(x, SearchableMixin):
                remove_from_index(x.__tablename__, x)
        session._changes = None

    @classmethod
    def reindex(cls):
        for x in cls.query:
            add_to_index(cls.__tablename__, x)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


# 多对多
followers = db.Table('followers',
                     db.Column('follower_id', db.Integer,
                               db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer,
                               db.ForeignKey('user.id'))
                     )


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True,
                         unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # followed是右边的，我关注了哪些人，我被哪些人关注
    # 'User'是关系的右侧实体（左侧实体是父类）。由于这是一种自我指涉关系，我必须在两边使用相同的类。
    # secondary 配置用于此关系的关联表，我在此类之上定义了该关联表。
    # primaryjoin表示将左侧实体（跟随者用户）与关联表链接的条件。关系左侧的连接条件是follower_id与关联表的字段匹配的用户ID 。所述followers.c.follower_id表达引用follower_id的关联表的列中。
    # secondaryjoin表示将右侧实体（跟随的用户）与关联表链接的条件。这个条件与for的类似primaryjoin，唯一不同的是现在我正在使用的followed_id，这是关联表中的另一个外键。
    # backref定义如何从右侧实体访问此关系。从左侧开始，关系被命名followed，因此从右侧我将使用该名称followers来表示链接到右侧目标用户的所有左侧用户。附加lazy参数表示此查询的执行模式。一种模式，dynamic将查询设置为在特定请求之前不运行，这也是我如何设置帖子的一对多关系。
    # lazy类似于同名参数backref，但这一个适用于左侧查询而不是右侧。
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def avatar(self, size=128):
        tmp = md5(self.email.lower().encode('utf-8')).hexdigest()  # d=mm
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(tmp, size)

    def set_password(self,  password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(followers, (followers.c.followed_id == Post.user_id))\
            .filter(followers.c.follower_id == self.id)

        own = Post.query.filter_by(user_id=self.id)

        return followed.union(own)\
            .order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires=600):
        # 链接有效时间10分钟,单位是秒
        token = jwt.encode({'reset_password': self.id, 'exp': time()+expires},
                           current_app.config['SECRET_KEY']).decode('utf-8')
        return token

    @staticmethod
    def verify_reset_password_token(token):
        try:
            user_id = jwt.decode(token, current_app.config['SECRET_KEY'])[
                'reset_password']
        except:
            return
        return User.query.get(user_id)

    def __repr__(self):
        return '<用户名：{}>'.format(self.username)


class Post(db.Model, SearchableMixin):
    __tablename__ = 'post'
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(10))

    def __repr__(self):
        return '<post {}>'.format(self.body)

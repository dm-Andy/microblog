from app import db, login
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5
import jwt
from time import time
from flask import current_app, url_for
from app.search import add_to_index, remove_from_index, query_index
import json
import redis
import rq
import base64
import os


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        result = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in result.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': result.pages,
                'total_items': result.total
            },
            '_links':{
                'self': url_for(endpoint,page=page,per_page=per_page,**kwargs),
                'next': url_for(endpoint,page=page + 1,per_page=per_page,**kwargs) if result.has_next else None,
                'prev': url_for(endpoint,page=page - 1,per_page=per_page,**kwargs) if result.has_prev else None
            }
        }
        return data

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


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return '<message {}>'.format(self.body)


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload = db.Column(db.Text())
    is_read = db.Column(db.Boolean,default=False,index=True) # 客户端轮询的时候的一个标记，如果没有改变就不发送数据到客户端

    def get_data(self):
        return json.loads(self.payload)

    def __repr__(self):
        return '<notification {}>'.format(self.name)


class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except(redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return job
    
    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100



class User(PaginatedAPIMixin, UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True,
                         unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_read_time = db.Column(db.DateTime)
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
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)


    sent_messages = db.relationship(
        'Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    received_messages = db.relationship(
        'Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    def unread_messages_count(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(receiver=self)\
            .filter(Message.timestamp > last_read_time)\
            .count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        noti = Notification(name=name,user=self,payload=json.dumps(data))
        db.session.add(noti)
        return noti

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

    def add_task(self, name, desc, *args, **kwargs):
        job = current_app.task_queue.enqueue('app.tasks.'+name,self.id,*args,**kwargs)
        task = Task(id=job.get_id(),name=name,description=desc,user=self)
        db.session.add(task)
        return task
    
    def get_tasks_in_progress(self):
        return self.tasks.filter_by(complete=False).all()
    
    def get_task_in_progress(self,name):
        return self.tasks.filter_by(name=name,complete=False).first()
    
    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + 'Z',
            'about_me': self.about_me,
            'post_count': self.posts.count(),
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
                'avatar': self.avatar(128)
            }
        }
        if include_email:
            data['email'] = self.email
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)
    
    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

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


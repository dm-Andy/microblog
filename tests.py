from app import create_app,db
from app.models import User,Post
import unittest
from datetime import datetime,timedelta
from config import TestConfig


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_password_hashing(self):
        u = User(username='andy')
        u.set_password('123')
        self.assertFalse(u.check_password('root'))
        self.assertTrue(u.check_password('123'))
    
    def test_avatar(self):
        u = User(username='andy', email='635885852@qq.com')
        self.assertEqual(u.avatar(128), 'https://www.gravatar.com/avatar/ed1a8459ade2aa868e3a3209ec9a6655?d=identicon&s=128')
    
    def test_follow(self):
        u1 = User(username='u1', email='u1@qq.com')
        u2 = User(username='u2', email='u2@qq.com')
        u1.set_password('123')
        u2.set_password('123')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u2.followed.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'u2')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'u1')

        u2.follow(u1)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'u2')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'u1')

        self.assertTrue(u2.is_following(u1))
        self.assertEqual(u2.followed.count(), 1)
        self.assertEqual(u2.followed.first().username, 'u1')
        self.assertEqual(u1.followers.count(), 1)
        self.assertEqual(u1.followers.first().username, 'u2')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

        self.assertTrue(u2.is_following(u1))
        self.assertEqual(u2.followed.count(), 1)
        self.assertEqual(u2.followed.first().username, 'u1')
        self.assertEqual(u1.followers.count(), 1)
        self.assertEqual(u1.followers.first().username, 'u2')
    
    def test_follow_posts(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        u1.set_password('123')
        u2.set_password('123')
        u3.set_password('123')
        u4.set_password('123')
        db.session.add_all([u1, u2, u3, u4])

        now = datetime.utcnow()
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])
if __name__ == '__main__':
    unittest.main(verbosity=2)


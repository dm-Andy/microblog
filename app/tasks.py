import time
from rq import get_current_job
from app import create_app, db
from app.models import Task, User, Post
import sys
import time
from app.email import send_email
import json
from flask import render_template


app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()

        task = Task.query.get(job.get_id())
        noti = task.user.add_notification('task_progress',{'task_id':task.id,'progress':progress})
        if progress >= 100:
            task.complete = True
            noti.is_read = True

        db.session.commit()

def export_posts(user_id):
    # rq不是flask，所以不会自动处理异常
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        posts = user.posts.order_by(Post.timestamp.asc())
        posts_count = posts.count()
        data = []
        i = 0
        for post in posts:
            data.append(dict(body=post.body,timestamp=post.timestamp.isoformat()+'Z'))
            time.sleep(3)
            i += 1
            _set_task_progress(i*100 // posts_count)

        send_email('[Microblog] Your blog posts',
                app.config['ADMINS'][0],
                [user.email],
                render_template('email/export_posts.txt',user=user),
                render_template('email/export_posts.html',user=user),
                [('posts.json', 'application/json',json.dumps(data,indent=4))],
                True)

    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
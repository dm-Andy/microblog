from app.main import bp
from app import db
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from app.main.forms import EditProfileForm, PostForm
from flask_login import current_user, login_required
from app.models import User, Post
from datetime import datetime
from flask_babel import _, get_locale
from guess_language import guess_language
from app.translate import translate
from app.main.forms import SearchForm
from math import ceil
'''
get_locale()  返回 zh_Hans_CN
guess_language  zh
moment 只有在zh_CN才翻译
'''


@bp.before_request
def before_request():
    # 获取语言设置到g
    g.locale = str(get_locale())
    if g.locale == 'zh_Hans_CN':
        # moment 认准zh_CN才翻译
        g.locale = 'zh_CN'

    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


def _get_paginate_url(query, endpoint, **kwargs):
    next_url = url_for(endpoint, page=query.next_num, **
                       kwargs) if query.has_next else None
    prev_url = url_for(endpoint, page=query.prev_num, **
                       kwargs) if query.has_prev else None
    return (next_url, prev_url)


def _get_page_num():
    page = request.args.get('page', 1, int)
    return page


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        # 确定语言，避免在每次加载的时候确定
        # 出错的几率大，有道的话直接用auto即可
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        if language == 'zh':
            language = 'zh_CN'
        post = Post(body=form.post.data,
                    author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('发表成功'))
        return redirect(url_for('main.index'))

    page = _get_page_num()
    posts = current_user.followed_posts()\
        .paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url, prev_url = _get_paginate_url(posts, 'main.index')
    pager = {
        'next_url': next_url,
        'prev_url': prev_url,
        'total': posts.total,
        'page': page,
        'page_count': ceil(posts.total/current_app.config['POSTS_PER_PAGE'])
    }
    return render_template('index.html', title=_('主页'), form=form, posts=posts.items,pager=pager)


@bp.route('/explore')
@login_required
def explore():
    page = _get_page_num()
    posts = Post.query.order_by(Post.timestamp.desc())\
        .paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url, prev_url = _get_paginate_url(posts, 'main.explore')

    return render_template('index.html', title=_('博客'), posts=posts.items, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()

    page = _get_page_num()
    posts = user.posts.order_by(Post.timestamp.desc())\
        .paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url, prev_url = _get_paginate_url(
        posts, 'main.user', username=user.username)

    return render_template('user.html', user=user, posts=posts.items, next_url=next_url, prev_url=prev_url, format=current_app.config['DATETIME_FORMAT'])


@bp.route('/user/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('修改成功'))
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('profile.html', title=_('个人资料编辑'), form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    return _process_follow(username, _('你不能关注自己'), _('关注 %(username)s 成功', username=username), True)


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    return _process_follow(username, _('你不能取关自己'), _('取消关注 %(username)s 成功', username=username), False)


def _process_follow(username, error, success, is_follow):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('用户%(username)s没有找到', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(error)
        return redirect(url_for('main.user', username=username))
    current_user.follow(user) if is_follow else current_user.unfollow(user)
    db.session.commit()
    flash(success)

    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
def translate_text():
    text, speak_url = translate(request.form['text'],
                                request.form['source_language'],
                                request.form['dest_language'])
    return jsonify(text=text, speak_url=speak_url)


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = _get_page_num()
    posts, total = Post.search(
        g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', page=page+1, q=g.search_form.q.data) if total > page * \
        current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', page=page-1,
                       q=g.search_form.q.data) if page > 1 else None
    return render_template('search.html', title=_('搜索'), posts=posts, total=total, next_url=next_url, prev_url=prev_url)

from app.api import bp
from flask import jsonify, request, url_for, g, abort
from app.models import User
from app import db
from app.api.errors import bad_request
from flask_babel import _
from app.api.auth import token_auth


def _get_page_num():
    page = request.args.get('page', 1, int)
    return page


def _get_per_page():
    per_page = request.args.get('per_page', 10, int)
    return per_page


def _get_meta():
    page = _get_page_num()
    per_page = _get_per_page()
    return (page, per_page)


@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    return jsonify(User.query.get_or_404(id).to_dict())


@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    page, per_page = _get_meta()
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')
    return jsonify(data)


@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    user = User.query.get_or_404(id)
    page, per_page = _get_meta()
    data = User.to_collection_dict(
        user.followers, page, per_page, 'api.get_followers', id=id)
    return jsonify(data)


@bp.route('/users/<int:id>/followed', methods=['GET'])
@token_auth.login_required
def get_followed(id):
    user = User.query.get_or_404(id)
    page, per_page = _get_meta()
    data = User.to_collection_dict(
        user.followed, page, per_page, 'api.get_followed', id=id)
    return jsonify(data)


@bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request(_('必须包含 username,email,password 字段'))
    if User.query.filter_by(username=data['username']).first():
        return bad_request(_('用户名已存在'))
    if User.query.filter_by(email=data['email']).first():
        return bad_request(_('该邮箱已注册'))
    
    user = User()
    user.from_dict(data,new_user=True)
    db.session.add(user)
    db.session.commit()
    res = jsonify(user.to_dict())
    res.status_code = 201
    res.headers['Location'] = url_for('api.get_user', id=user.id)
    return res


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):
    if g.current_user.id != id:
        abort(403)
        
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    if 'username' in data and data['username'] != user.username and \
            User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if 'email' in data and data['email'] != user.email and \
            User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')
    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())

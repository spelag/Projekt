from app import app, db
from flask import render_template, request, redirect, url_for, jsonify, session, flash
from app.models import User, login_manager
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/register', methods=["POST"])
def register():
    form = request.form
    user = User(
        username=form['username'],
        email=form['e-mail']
    )
    user.set_password(form['password'])
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('login'))

@app.route('/register-validation', methods=["POST"])
def registerValidation():
    if request.method == "POST":
        emailAdd = request.get_json()['email']
        if User.query.filter_by(email=emailAdd).first():
            return jsonify({"user_exists": "true"})
        else:
            return jsonify({"user_exists": "false"})

@app.route('/signin', methods=["POST"])
def signin():
    form = request.form
    user = User.query.filter_by(email=form['e-mail']).first()
    if not user:
        flash("There is no account with this e-mail.")
        return redirect(url_for('login'))
    if user.check_password(form['password']):
        if form['remember-me']:
            login_user(user, remember=True)
        else:
            login_user(user)
        return user.username + ", you are successfully logged in."
    else:
        flash("Wrong password. Try again.")
        return redirect(url_for('login'))

@app.route('/logout', methods=["POST", "GET"])
def logout():
    logout_user()
    return "You are now logged out."

@app.route('/match')
def match():
    return render_template('match.html')

@app.route('/newmatch')
def newMatch():
    return render_template('newmatch.html')
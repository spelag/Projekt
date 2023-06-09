from datetime import datetime
from app import app, db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    join_date = db.Column(db.DateTime(timezone=True), default=datetime.now)
    experience = db.Column(db.String(12))
    age_group = db.Column(db.String(6))
    location = db.Column(db.String(120))

    friends = db.relationship('Friend', backref='user', lazy=True)
    requests = db.relationship('FriendRequest', backref='user', lazy=True)
    invites = db.relationship('Invites', backref='user', lazy=True)
    outboundInvites = db.relationship('Match', backref='user', lazy=True)
    wins = db.relationship('Wins', backref='user', lazy=True)
    losses = db.relationship('Losses', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    friendID = db.Column(db.Integer, nullable=False)
    friendOG = db.Column(db.Integer, db.ForeignKey('user.id'))

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester = db.Column(db.Integer, nullable=False)
    requested = db.Column(db.Integer, db.ForeignKey('user.id'))

class Wins(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    winner = db.Column(db.Integer, db.ForeignKey('user.id'))
    match = db.relationship('Match', backref='wins', lazy=True)

class Losses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loser = db.Column(db.Integer, db.ForeignKey('user.id'))
    match = db.relationship('Match', backref='losses', lazy=True)

class Invites(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inviter = db.Column(db.Integer)
    invitee = db.Column(db.Integer, db.ForeignKey('user.id'))
    match = db.relationship('Match', backref='invites', lazy=True)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique = db.Column(db.String(10), nullable=False)
    inviter = db.Column(db.Integer, db.ForeignKey('user.id'))
    invitee = db.Column(db.Integer)
    invite = db.Column(db.Integer, db.ForeignKey('invites.id'))
    winner = db.Column(db.Integer, db.ForeignKey('wins.id'))
    loser = db.Column(db.Integer, db.ForeignKey('losses.id'))
    winnerPoints = db.Column(db.String(10))
    loserPoints = db.Column(db.String(10))
    sets = db.Column(db.Integer)
    setResults = db.Column(db.String(30))
    matchDate = db.Column(db.DateTime(timezone=True))
    started = db.Column(db.Boolean)
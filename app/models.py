from datetime import datetime
from app import app, db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

from sqlalchemy import or_

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    # friend who requested
    friendA = db.Column(db.Integer, nullable=False)
    # friend who accepted
    friendB = db.Column(db.Integer, nullable=False)
    # the matches they played
    matches = db.Relationship('Match', back_populates='friendship')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    join_date = db.Column(db.DateTime(timezone=True), default=datetime.now)
    experience = db.Column(db.String(12))
    age_group = db.Column(db.String(6))
    location = db.Column(db.String(120))

    # inboundRequests = db.relationship('FriendRequest', back_populates='requested', lazy=True)
    # outboundRequests = db.relationship('FriendRequest', back_populates='requester', lazy=True)
    # inboundInvites = db.relationship('Match', back_populates='invitee', lazy=True)
    # outboundInvites = db.relationship('Match', back_populates='inviter', lazy=True)

    def get_friends(self):
        friends = []
        a = Friendship.query.filter(or_(Friendship.friendA==self.id, Friendship.friendB==self.id))
        for i in a:
            if i.friendA == self.id:
                friends.append(User.query.get(i.friendB))
            elif i.friendB == self.id:
                friends.append(User.query.get(i.friendA))
        return friends
    
    def get_requests(self):
        requests = []
        a = FriendRequest.query.filter(FriendRequest.requested==self.id)
        for i in a:
            requests.append(i)
        return requests

    def get_requested(self):
        requests = []
        a = FriendRequest.query.filter(FriendRequest.requester==self.id)
        for i in a:
            requests.append(i)
        return requests

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    requester = db.Column(db.Integer)
    requested = db.Column(db.Integer)

    # requested = db.relationship('User', back_populates='inboundRequests', lazy=True)
    # requester = db.relationship('User', back_populates='outboundRequests', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    unique = db.Column(db.String(10), nullable=False)
    # winnerPoints = db.Column(db.String(10))
    # loserPoints = db.Column(db.String(10))
    # sets = db.Column(db.Integer)
    # setResults = db.Column(db.String(30))
    setiCount = db.Column(db.Integer)
    matchDate = db.Column(db.DateTime(timezone=True))
    started = db.Column(db.Boolean)
    
    # foreign keys ig
    friendship_id = db.Column(db.Integer, db.ForeignKey('friendships.id'))
    
    # the two friends playing the match
    friendship = db.relationship('Friendship', back_populates='matches', lazy=True)
    
    # the winner and the loser
    winner = db.Column(db.Integer)
    loser = db.Column(db.Integer)

    # the invite before the match
    invite = db.relationship('Invite', back_populates='match', lazy=True)

    # the sets played within this match
    sets = db.relationship('Set', back_populates='match', lazy=True)


class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inviter = db.Column(db.Integer)
    invitee = db.Column(db.Integer)

    match = db.relationship('Match', back_populates='invite', lazy=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scoreW = db.Column(db.Integer)
    scoreL = db.Column(db.Integer)

    winner = db.Column(db.Integer)
    loser = db.Column(db.Integer)

    match = db.relationship('Match', back_populates='sets', lazy=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
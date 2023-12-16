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

    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    location = db.relationship('Location', back_populates='users')
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

    def get_inboundInvites(self):
        invites = []
        a = Invite.query.filter(Invite.invitee==self.id)
        for i in a:
            invites.append(User.query.get(i.inviter))
        return invites
    def get_outboundInvites(self):
        invites = []
        a = Invite.query.filter(Invite.inviter==self.id)
        for i in a:
            invites.append(User.query.get(i.invitee))
        return invites

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    requester = db.Column(db.Integer)
    requested = db.Column(db.Integer)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    unique = db.Column(db.String(10), nullable=False)
    notes = db.Column(db.Text())
    timeSuggestion = db.Column(db.String(60))
    timeConfirmA = db.Column(db.Boolean)
    timeConfirmB = db.Column(db.Boolean)
    # winnerPoints = db.Column(db.String(10))
    # loserPoints = db.Column(db.String(10))
    # sets = db.Column(db.Integer)
    # setResults = db.Column(db.String(30))
    setiCount = db.Column(db.Integer)
    matchDate = db.Column(db.DateTime(timezone=True))
    started = db.Column(db.Boolean)
    
    # foreign keys ig
    friendship_id = db.Column(db.Integer, db.ForeignKey('friendships.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    
    # the two friends playing the match
    friendship = db.relationship('Friendship', back_populates='matches')

    # tag the match
    tag = db.relationship('Tag', back_populates='matches')

    # the location
    location = db.relationship('Location', back_populates='matches')

    # the winner and the loser
    winner = db.Column(db.Integer)
    loser = db.Column(db.Integer)

    # the sets played within this match
    sets = db.relationship('Set', back_populates='match', lazy=True)

    def setCount(self):
        set1 = 0
        set2 = 0
        for i in self.sets:
            if i.winner != None:
                if i.scoreL > i.scoreW:
                    set1 += 1
                else:
                    set2 += 1
        return [set1, set2]

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(60))

    matches = db.relationship('Match', back_populates='tag')

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(60))

    users = db.relationship('User', back_populates='location')
    matches = db.relationship('Match', back_populates='location')

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inviter = db.Column(db.Integer)
    invitee = db.Column(db.Integer)

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # actually score1 and score2, to get winner just check which one is bigger
    scoreL = db.Column(db.Integer)
    scoreW = db.Column(db.Integer)

    winner = db.Column(db.Integer)
    loser = db.Column(db.Integer)

    match = db.relationship('Match', back_populates='sets', lazy=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
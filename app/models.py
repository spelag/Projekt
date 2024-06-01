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
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(320), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    join_date = db.Column(db.DateTime(timezone=True), default=datetime.now)
    experience = db.Column(db.String(12))
    age_group = db.Column(db.String(6))
    is_admin = db.Column(db.Boolean, default=0)

    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    location = db.relationship('Location', back_populates='users')
    # inboundRequests = db.relationship('FriendRequest', back_populates='requested', lazy=True)
    # outboundRequests = db.relationship('FriendRequest', back_populates='requester', lazy=True)
    # inboundInvites = db.relationship('Match', back_populates='invitee', lazy=True)
    # outboundInvites = db.relationship('Match', back_populates='inviter', lazy=True)
    notifications = db.Relationship('Notification', back_populates='user', order_by='Notification.id.desc()')

    klub_id = db.Column(db.Integer, db.ForeignKey('klubs.id'))
    klub = db.relationship('Klub', back_populates='members')

    skupinas = db.relationship('Skupina', secondary = 'skupina_user', back_populates='members')

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

    requester = db.Column(db.Integer)
    requested = db.Column(db.Integer)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    unique = db.Column(db.String(10), nullable=False)
    notes = db.Column(db.Text())
    setiCount = db.Column(db.Integer)
    date = db.Column(db.DateTime(timezone=True))
    finished = db.Column(db.Boolean)
    confirmA = db.Column(db.Boolean)
    confirmB = db.Column(db.Boolean)

    # foreign keys ig
    friendship_id = db.Column(db.Integer, db.ForeignKey('friendships.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    skupina_id = db.Column(db.Integer, db.ForeignKey('skupinas.id'))

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

    # skupina v turnirju if applicable
    skupina = db.relationship('Skupina', back_populates='matches')

    def setCount(self):
        set1 = 0
        set2 = 0
        for i in self.sets:
            if i.winner != None:
                if i.scoreA > i.scoreB:
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
    klubs = db.relationship('Klub', back_populates='location')

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inviter = db.Column(db.Integer)
    invitee = db.Column(db.Integer)

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    scoreA = db.Column(db.Integer)
    scoreB = db.Column(db.Integer)

    winner = db.Column(db.Integer)
    loser = db.Column(db.Integer)

    match = db.relationship('Match', back_populates='sets', lazy=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text())
    read = db.Column(db.Boolean)
    type = db.Column(db.String(3))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='notifications')

class Klub(db.Model):
    __tablename__ = 'klubs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    admin = db.Column(db.Integer, nullable=False)

    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    location = db.relationship('Location', back_populates='klubs')

    members = db.Relationship('User', back_populates='klub')
    turnirs = db.Relationship('Turnir', back_populates='klub')

class Turnir(db.Model):
    __tablename__ = 'turnirs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    description = db.Column(db.String(320), nullable=False)
    type = db.Column(db.String(3), nullable=False)
    ongoing = db.Column(db.Boolean, default=1)

    skupinas = db.Relationship('Skupina', back_populates='turnir')

    klub_id = db.Column(db.Integer, db.ForeignKey('klubs.id'))
    klub = db.relationship('Klub', back_populates='turnirs')

class Skupina(db.Model):
    __tablename__ = 'skupinas'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)

    members = db.Relationship('User', secondary='skupina_user', back_populates='skupinas')

    matches = db.Relationship('Match', back_populates='skupina')

    turnir_id = db.Column(db.Integer, db.ForeignKey('turnirs.id'))
    turnir = db.relationship('Turnir', back_populates='skupinas')

skupina_user = db.Table(
    'skupina_user',
    db.Column('skupina_id', db.Integer, db.ForeignKey('skupinas.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)
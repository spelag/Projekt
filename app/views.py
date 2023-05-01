from app import app, db, socketio
from flask import render_template, request, redirect, url_for, jsonify, session, flash
from app.models import User, FriendRequest, Friend, Match, Invites, Wins, Losses, login_manager
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sqlalchemy import text, update
import random
from string import ascii_letters
from flask_socketio import join_room, leave_room, send, emit
from datetime import datetime

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
    login_user(user, remember=False)
    return redirect(url_for('index'))

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
        if len(form) == 2:
            login_user(user, remember=False)
        else:
            login_user(user, remember=True)
        return redirect(url_for('index'))
    else:
        flash("Wrong password. Try again.")
        return redirect(url_for('login'))

@app.route('/logout', methods=["POST", "GET"])
def logout():
    logout_user()
    return redirect(url_for('index'))

def generate_unique_code(length):
    while True:
        code = ""
        for i in range(length):
            code += random.choice(ascii_letters)
        if code not in matches:
            break
    return code

matches = []

@app.route('/match/<matchID>/<unique>')
def match(matchID, unique):
    u1 = Match.query.filter_by(id=matchID).first().invitee
    u2 = Match.query.filter_by(id=matchID).first().inviter
    u1 = User.query.filter_by(id=u1).first()
    u2 = User.query.filter_by(id=u2).first()
    if current_user.id != u1.id and current_user.id != u2.id:
        return redirect(url_for('index'))
    return render_template('match.html', u1=u1, u2=u2, unique=unique, u1Score=0, u2Score=0, matchID=matchID)

@socketio.on('score')
def score(data):
    serva = data["serva"]
    turn = data["turn"]
    if data["what"] == "plus":
        data[data["who"]] += 1
        serva += 1
    else:
        data[data["who"]] -= 1
        if serva != 0:
            serva -= 1
    if data[data["who"]] == 11:
        emit('gameOver', {"winner":data["who"]}, room=data["room"])
    else:
        if serva%4 == 0:
            turn = data["starter"]
        elif serva%2 == 0:
            turn = data["notstarter"]
        elif serva%4 == 1:
            turn = data["starter"]
        elif serva%4 == 3:
            turn = data["notstarter"]
        if data[data["who"]] >= 0:
            emit('score', {"turn":turn, "serva":serva, "0":data["0"], "1":data["1"]}, room=data['room'])

readyUsers = []

@socketio.on('start')
def start(data):
    if not (data['user'] in readyUsers):
        readyUsers.append(data['user'])
        emit('start', {"user":data['user'], "ready": False}, room=data['matchID'])
    if len(readyUsers) == 2:
        Match.query.filter_by(id=data['matchID']).first().matchDate = datetime.now
        emit('start', {"user":data['user'], "ready": True, "starter":str(random.choice([1,2]))}, room=data['matchID'])

@socketio.on('join')
def join(data):
    join_room(data['room'])

@socketio.on('leave')
def leave(data):
    leave_room(data['room'])

@app.route('/newmatch/<opponent>')
def newMatch(opponent):
    opponent = User.query.filter_by(id=opponent).first()
    if Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first():
        flash("You already invited this user for a match.")
        return redirect(url_for('profile', username=opponent.username, userID=opponent.id))
    unique = generate_unique_code(10)
    invite = Invites(
        inviter = current_user.id,
        invitee = opponent.id
    )
    db.session.add(invite)
    db.session.commit()
    match = Match(
        unique = unique,
        inviter = current_user.id,
        invitee = opponent.id,
        invite = invite.id
    )
    db.session.add(match)
    db.session.commit()
    matches.append(match.id)
    return render_template('matchSettings.html', opponent=opponent, unique=unique, matchID=match.id)

@app.route('/match/<matchID>/<unique>/chat')
def chat(matchID, unique):
    u2 = Match.query.filter_by(id=matchID).first().invitee
    return render_template('chat.html', u2=u2)

@app.route('/invites')
def invites():
    return render_template('invites.html', invitesLen=len(current_user.invites), invitedLen=len(current_user.outboundInvites), User=User, Match=Match)

@app.route('/decline/<invite>')
def declineInvite(invite):
    match = Match.query.filter_by(invite=invite).first()
    invite = Invites.query.filter_by(id=invite).first()
    db.session.delete(invite)
    db.session.delete(match)
    db.session.commit()
    return redirect(url_for('invites'))

@app.route('/profile/<username>/<userID>')
def profile(username, userID):
    user = User.query.filter_by(id=userID).first()
    if not current_user.is_active:
        return render_template('profile.html', loggedin=False, user=user)
    elif int(userID) == current_user.id:
        return render_template('profileSettings.html')
    friends=Friend.query.filter_by(friendOG=current_user.id, friendID=userID).first()
    requests=FriendRequest.query.filter_by(requested=current_user.id, requester=userID).first()
    alreadyRequested=FriendRequest.query.filter_by(requester=current_user.id, requested=userID).first()
    if friends == None:
        if requests == None:
            if alreadyRequested == None:
                return render_template('profile.html', loggedin=True, user=user, friend=False, request=False, impending=False)
            return render_template('profile.html', loggedin=True, user=user, friend=False, request=False, impending=True)
        return render_template('profile.html', loggedin=True, user=user, friend=False, request=True)
    return render_template('profile.html', loggedin=True, user=user, friend=True)

@app.route('/editprofile', methods=["GET", "POST"])
def editProfile():
    if request.method == "GET":
        return render_template('editProfile.html')
    info = request.form
    current_user.age_group = info['age']
    current_user.location = info['location']
    current_user.experience = info['experience']
    db.session.commit()
    return redirect(url_for('profile', username=current_user.username, userID=current_user.id))

@app.route('/members/<who>')
def allusers(who):
    btnA = "secondary"
    btnF = "secondary"
    btnR = "secondary"
    if who == "friends":
        allUsers = []
        for i in current_user.friends:
            allUsers.append(User.query.filter_by(id=i.friendID).first())
        userCount = len(allUsers)
        btnF = "primary"
    elif who == "friendrequests":
        allUsers = []
        for i in current_user.requests:
            allUsers.append(User.query.filter_by(id=i.requester).first())
        userCount = len(allUsers)
        btnR = "primary"
    else:
        allUsers = db.session.query(User)
        userCount = allUsers.count()
        btnA = "primary"
    return render_template('allusers.html', userCount=userCount, allUsers=allUsers, loggedin=current_user.is_active, btnA=btnA, btnF=btnF, btnR=btnR)

@app.route('/addfriend/<friendName>/<friendID>')
def addFriend(friendName, friendID):
    friend = Friend.query.filter_by(friendOG=current_user.id, friendID=friendID).first()
    if friend:
        flash("You are already friends with this user.")
        return redirect(url_for('allusers'))
    friend = Friend(
        friendID = current_user.id,
        friendOG = friendID)
    db.session.add(friend)
    friend = Friend(
        friendOG = current_user.id,
        friendID = friendID)
    db.session.add(friend)
    if FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first():
        db.session.delete(FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first())
    else:
        db.session.delete(FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first())
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removefriend/<friendName>/<friendID>')
def removeFriend(friendName, friendID):
    db.session.delete(Friend.query.filter_by(friendOG=current_user.id, friendID=friendID).first())
    db.session.delete(Friend.query.filter_by(friendID=current_user.id, friendOG=friendID).first())
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/friendrequest/<friendName>/<friendID>')
@login_required
def friendRequest(friendName, friendID):
    request = FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first()
    if request:
        flash("A friend request has already been sent.")
        return redirect(url_for('allusers'))
    friendRequest = FriendRequest(
        requester = current_user.id,
        requested = friendID)
    db.session.add(friendRequest)
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))
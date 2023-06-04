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
    if current_user.is_authenticated:
        return render_template('loggedinHomepage.html')
    return render_template('homepage.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template('signup.html', mail="")
    return render_template('signup.html', mail=request.form["emailAddress"])

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

@app.route('/logout')
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
        serva = 0
        emit('gameOver', {"winner":data["who"], "serva":serva}, room=data["room"])
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

@socketio.on('setAdjust')
def setAdjust(data):
    serva = 0
    if data["what"] == "plus":
        emit('gameOver', {"serva":serva, "winner":data["who"]}, room=data["room"])
    else:
        data[data["who"]] -= 1
        if data[data["who"]] >= 0:
            emit('setiMinus', {"serva":serva, "0":data["0"], "1":data["1"]}, room=data['room'])

readyUsers = {}

@socketio.on('start')
def start(data):
    if len(readyUsers[data["matchID"]]) == 1:
        Match.query.filter_by(id=data['matchID']).first().matchDate = datetime.now()
        # match.matchDate = datetime.utcnow
        db.session.commit()
        readyUsers[data["matchID"]].append(data['user'])
        emit('start', {"user":data['user'], "ready": True, "starter":str(random.choice([1,2]))}, room=data['matchID'])
    else:
        readyUsers[data["matchID"]].append(data['user'])
        emit('start', {"user":data['user'], "ready": False}, room=data['matchID'])

@socketio.on('setiChange')
def setiChange(data):
    if str(data['matchID']) in readyUsers:
        readyUsers.pop(data["matchID"]) 
    emit('setiChange', data, room=data['matchID'])

@socketio.on('join')
def join(data):
    if data["room"] not in readyUsers:
        readyUsers[data["room"]] = []
    join_room(data['room'])

@socketio.on('leave')
def leave(data):
    leave_room(data['room'])
    if readyUsers[data['room']][0] == data['user']:
        readyUsers[data['room']][0] = readyUsers[data['room']][0]
        readyUsers[data['room']].pop()
    else:
        readyUsers[data['room']].pop()
    if len(readyUsers[data['room']]) == 0:
        del readyUsers[data['room']]
    return redirect(url_for('pastmatches'))

@socketio.on('changeResult')
def changeResult(data):
    emit('changeResult', room=data["matchID"])

@app.route('/newmatch/<opponent>')
def newMatch(opponent):
    opponent = User.query.filter_by(id=opponent).first()
    m2 = Match.query.filter_by(invitee=current_user.id, inviter=opponent.id).first()
    if not Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first() and not m2:
        unique = generate_unique_code(10)
        matches.append(unique)
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
        return render_template('matchSettings.html', opponent=opponent, unique=unique, matchID=match.id)
    elif m2:
        match = m2
        unique = match.unique        
    else:
        match = Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first()
        unique = match.unique
    return redirect(url_for('chat', matchID=match.id, unique=unique))

@socketio.on('save')
def save(data):
    match = Match.query.filter_by(id=data["matchID"]).first()
    if data["waiting"]:
        emit("stopWait", room=data["room"])
        return
    match.loser = data["loser"]
    match.winnerPoints = data["winP"]
    match.loserPoints = data["losP"]
    match.sets = data["seti"]
    match.setResults = data["setRez"]
    db.session.commit()
    emit("leave", room=data["room"])

@app.route('/pastmatches')
def pastmatches():
    return render_template('pastmatches.html', User=User, allInviter=Match.query.filter_by(inviter=current_user.id), allInvitee=Match.query.filter_by(invitee=current_user.id))

chats = {}

@app.route('/match/<matchID>/<unique>/chat')
def chat(matchID, unique):
    u1 = User.query.filter_by(id=Match.query.filter_by(id=matchID).first().invitee).first()
    u2 = User.query.filter_by(id=Match.query.filter_by(id=matchID).first().inviter).first()
    return render_template('chat.html', u1=u1, u2=u2, matchID=matchID, Match=Match, unique=unique)

@socketio.on('joinChat')
def join(data):
    join_room(data['room'])
    send({"name": data["name"], "message": "has entered the chat"}, to=data["room"])

@socketio.on('leaveChat')
def leave(data):
    leave_room(data['room'])
    send({"name": data["name"], "message": "has left the chat"}, to=data["room"])

@socketio.on("message")
def message(data):
    send({"name": data["who"], "message": data["message"]}, to=data["room"])

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
    return render_template('allusers.html', userCount=userCount, allUsers=allUsers, loggedin=current_user.is_active, btnA=btnA, btnF=btnF, btnR=btnR, Friend=Friend, FriendRequest=FriendRequest)

@app.route('/addfriend/<friendName>/<friendID>')
def addFriend(friendName, friendID):
    friend = Friend.query.filter_by(friendOG=current_user.id, friendID=friendID).first()
    if FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first():
        db.session.delete(FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first())
    else:
        db.session.delete(FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first())
    if friend:
        flash("You are already friends with this user.")
        return redirect(url_for('allusers', who="friends"))
    friend = Friend(
        friendID = current_user.id,
        friendOG = friendID)
    db.session.add(friend)
    friend = Friend(
        friendOG = current_user.id,
        friendID = friendID)
    db.session.add(friend)
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removefriend/<friendName>/<friendID>')
def removeFriend(friendName, friendID):
    db.session.delete(Friend.query.filter_by(friendOG=current_user.id, friendID=friendID).first())
    db.session.delete(Friend.query.filter_by(friendID=current_user.id, friendOG=friendID).first())
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removerequest/<friendID>')
def removeRequest(friendID):
    if FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first():
        db.session.delete(FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first())
    else:
        db.session.delete(FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first())
    db.session.commit()
    return redirect(url_for('allusers', who="friendrequests"))

@app.route('/friendrequest/<friendName>/<friendID>')
@login_required
def friendRequest(friendName, friendID):
    request = FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first()
    if request:
        flash("A friend request has already been sent.")
        return redirect(url_for('allusers', who="all"))
    friendRequest = FriendRequest(
        requester = current_user.id,
        requested = friendID)
    db.session.add(friendRequest)
    db.session.commit()
    return redirect(url_for('allusers', who="all"))
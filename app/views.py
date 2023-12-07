from app import app, db, socketio
from flask import render_template, request, redirect, url_for, jsonify, flash, send_file
from app.models import User, FriendRequest, Friendship, Match, Invite, login_manager
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sqlalchemy import text, update, select, or_
import random
from string import ascii_letters
from flask_socketio import join_room, leave_room, send, emit
from datetime import datetime
import csv

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
        flash("Wrong credidentials.")
        return redirect(url_for('login'))
    if user.check_password(form['password']):
        if len(form) == 2:
            login_user(user, remember=False)
        else:
            login_user(user, remember=True)
        return redirect(url_for('index'))
    else:
        flash("Wrong credidentials.")
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
        readyUsers[data["matchID"]] = []
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
        readyUsers[data['room']][0] = readyUsers[data['room']][1]
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

    invite = Invite.query.filter(or_(Invite.inviter==current_user.id, Invite.invitee==current_user.id), or_(Invite.inviter==opponent.id, Invite.invitee==opponent.id)).first()
    if invite:
        flash("Such invite already exists.")
        return redirect(url_for('invites'))

    invite = Invite(
        inviter = current_user.id,
        invitee = opponent.id
    )
    db.session.add(invite)
    db.session.commit()
    return

    # m2 = Match.query.filter_by(invitee=current_user.id, inviter=opponent.id).first()
    # if (not Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first() and not m2) or (m2.started == False or Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first().started == False):
    #     unique = generate_unique_code(10)
    #     matches.append(unique)
    #     db.session.add(invite)
    #     db.session.commit()
    #     match = Match(
    #         unique = unique,
    #         inviter = current_user.id,
    #         invitee = opponent.id,
    #         invite = invite.id,
    #         started = True
    #     )
    #     db.session.add(match)
    #     db.session.commit()
    #     return render_template('matchSettings.html', opponent=opponent, unique=unique, matchID=match.id)
    # elif m2:
    #     match = m2
    #     unique = match.unique        
    # else:
    #     match = Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first()
    #     unique = match.unique
    # return redirect(url_for('chat', matchID=match.id, unique=unique))

@socketio.on('save')
def save(data):
    match = Match.query.filter_by(id=data["matchID"]).first()
    if data["waiting"]:
        emit("stopWait", room=data["room"])
        return
    match.loser = data["loser"]
    match.winner = data["winner"]
    match.winnerPoints = data["winP"]
    match.loserPoints = data["losP"]
    match.sets = data["seti"]
    match.setResults = data["setRez"]
    match.started = False
    match.inviter = None
    print(match.invite)
    db.session.delete(Invite.query.filter_by(id=match.invite).first())
    db.session.commit()
    emit("leave", room=data["room"])

@app.route('/pastmatches')
def pastmatches():
    a = (db.session.query(User).where(User.id == current_user.id)).first()
    b = (select(Match).where(Match.winner == current_user.id).where(Match.loser == current_user.id))
    d = (Match.query.filter(or_(Match.winner==current_user.username, Match.loser==current_user.username)).order_by(Match.matchDate.desc()))
    for i in d:
        print(i)
        print(i.winner)
    print(a)
    print(a.friends)
    print(d.all())

    # allInviter=Match.query.filter_by(winner=current_user.username), allInvitee=Match.query.filter_by(loser=current_user.username)
    return render_template('pastmatches.html', user=current_user, User=User, matches=d)

@app.route('/pastmatches/sort/<what>/<type>')
def pastmatchesSort(what, type):
    if what == "date":
        if type == "desc":
            d = (Match.query.filter(or_(Match.winner==current_user.username, Match.loser==current_user.username)).order_by(Match.matchDate.desc()))
        elif type == "incr":
            d = (Match.query.filter(or_(Match.winner==current_user.username, Match.loser==current_user.username)).order_by(Match.matchDate))
    elif what == "winner":
        if type == "desc":
            d = (Match.query.filter(or_(Match.winner==current_user.username, Match.loser==current_user.username)).order_by(Match.winner.desc()))
        elif type == "incr":
            d = (Match.query.filter(or_(Match.winner==current_user.username, Match.loser==current_user.username)).order_by(Match.winner))

    return render_template('pastmatches.html', user=current_user, User=User, matches=d)

@app.route('/pastmatches/export')
def export():
    matches = Match.query.filter(or_(Match.winner == current_user.username, Match.loser == current_user.username))
    with open('export.csv', 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["winner", "loser", "sets", "winnerSet", "loserSet", "winnerPoints1", "winnerPoints2", "winnerPoints3", "loserPoints1", "loserPoints2", "loserPoints3", "date"])
        for m in matches:
            writer.writerow([m.winner, m.loser, m.sets, m.setResults[0], m.setResults[1], m.winnerPoints[:2], m.winnerPoints[2:4], m.winnerPoints[4:], m.loserPoints[:2], m.loserPoints[2:4], m.loserPoints[4:], m.matchDate])

    fName = current_user.username + 'PingPongerExport.csv'
    return send_file('../export.csv', mimetype='type/csv', download_name=fName, as_attachment=True)

@app.route('/match/<id>')
def oneMatch(id):
    match = Match.query.filter(Match.id == id).first()
    return render_template('onematch.html', user=current_user, match=match, User=User)


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
    invites = current_user.get_inboundInvites()
    invited = current_user.get_outboundInvites()
    print(invites)
    print(invited)
    return render_template('invites.html', invitesLen=len(invites), invitedLen=len(invited), invites=invites, invited=invited)

@app.route('/decline/<invite>')
def declineInvite(invite):
    match = Match.query.filter_by(invite=invite).first()
    invite = Invite.query.filter_by(id=invite).first()
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
    friends=Friendship.query.filter(or_(Friendship.friendA==current_user.id, Friendship.friendB==current_user.id), or_(Friendship.friendB==userID, Friendship.friendA==userID)).first()
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

    friends = current_user.get_friends()
    requested = []
    for i in current_user.get_requested():
        requested.append(User.query.filter_by(id=i.requested).first())
    requester = []
    for i in current_user.get_requests():
        requester.append(User.query.filter_by(id=i.requester).first())

    if who == "friends":
        print(current_user.get_friends())
        allUsers = friends
        userCount = len(allUsers)
        btnF = "primary"
    elif who == "friendrequests":
        allUsers = requester
        userCount = len(allUsers)
        btnR = "primary"
    else:
        allUsers = db.session.query(User)
        userCount = allUsers.count()
        btnA = "primary"
    print(requested, allUsers)
    return render_template('allusers.html', userCount=userCount, allUsers=allUsers, loggedin=current_user.is_active, btnA=btnA, btnF=btnF, btnR=btnR, friends=friends, requested=requested, requester=requester)

@app.route('/addfriend/<friendName>/<friendID>')
def addFriend(friendName, friendID):
    friend = Friendship.query.filter_by(friendA=current_user.id, friendB=friendID).first()
    if FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first():
        db.session.delete(FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first())
    else:
        db.session.delete(FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first())
    if friend:
        flash("You are already friends with this user.")
        return redirect(url_for('allusers', who="friends"))
    friend = Friendship(
        friendB = current_user.id,
        friendA = friendID)
    db.session.add(friend)
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removefriend/<friendName>/<friendID>')
def removeFriend(friendName, friendID):
    a = (Friendship.query.filter_by(friendA=current_user.id, friendB=friendID).first())
    if not a:
        a = Friendship.query.filter_by(friendB=current_user.id, friendA=friendID).first()
    db.session.delete(a)
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
    flash("Friend request sent successfully.")
    return redirect(url_for('allusers', who="all"))
from app import app, db, socketio
from flask import render_template, request, redirect, url_for, jsonify, flash, send_file, session
from app.models import User, FriendRequest, Friendship, Match, Invite, Location, Tag, Set, login_manager
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
    session['url'] = url_for('index')
    if current_user.is_authenticated:
        matches = []
        # friendships = Friendship.query.filter(or_(Friendship.friendA==current_user.id, Friendship.friendB==current_user.id))
        # for i in friendships:
        #     matches.append(i.matches)
        temp = Match.query.filter(Match.finished==False).all()
        for i in temp:
            if i.friendship.friendA==current_user.id or i.friendship.friendB==current_user.id:
                matches.append(i)
        return render_template('loggedinHomepage.html', User=User, matches=matches, length=len(matches))
    return render_template('homepage.html')

@app.route('/login')
def login():
    return render_template('login.html')

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
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/notifications')
@login_required
def notifications():
    session['url'] = url_for('notifications')
    return render_template('notifications.html')

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
@login_required
def match(matchID, unique):
    match = Match.query.get(matchID)

    if len(match.sets) >= match.setiCount:
        flash("You've already played this match.")
        return redirect(url_for('oneMatch', id=match.id))

    u1 = User.query.get(match.friendship.friendA)
    u2 = User.query.get(match.friendship.friendB)
    return render_template('match.html', u1=u1, u2=u2, unique=unique, u1Score=0, u2Score=0, matchID=matchID)

@socketio.on('score')
def score(data):
    match = Match.query.get(data["room"])
    set = match.sets[-1]
    if data["what"] == "plus":
        if data["who"] == "1":
            set.scoreW += 1
        else:
            set.scoreL += 1
        if max(set.scoreW, set.scoreL) >= 11 and max(set.scoreW, set.scoreL) - min(set.scoreW, set.scoreL) >= 2:
            if set.scoreL > set.scoreW:
                set.winner = match.friendship.friendA
                set.loser = match.friendship.friendB
            else:
                set.loser = match.friendship.friendA
                set.winner = match.friendship.friendB
            if match.setiCount == len(match.sets):
                match.confirmA = False
                match.confirmB = False
                emit('redirect', {"url": url_for('oneMatch', id=data["room"])}, room=data["room"])
            else:
                newSet = Set()
                newSet.scoreL = 0
                newSet.scoreW = 0
                newSet.match = match
                db.session.add(newSet)
                emit('updateSet', {"to": set.winner}, room=data["room"])
            db.session.commit()
            return
    if data["what"] == "minus":
        if data["who"] == "1":
            if set.scoreW > 0:
                set.scoreW -= 1
        else:
            if set.scoreL > 0:
                set.scoreL -= 1
    emit('score', {"score1": set.scoreL, "score2": set.scoreW}, room=data["room"])
    db.session.commit()

confirmation = {}
@socketio.on('finalize')
def finalize(data):
    if data["what"] == "ok":
        match = Match.query.get(data["room"])
        if data["user"] == match.friendship.friendA:
            print('help.')
        else:
            confirmation[data["room"]] = 1
    elif data["what"] == "change":
        if data["room"] in confirmation:
            confirmation.pop(data["room"])
        emit('confirm', {"winner":"test", "u1score": data["u1score"], "u2score": data["u2score"], "setiCount": data["setiCount"]}, room=data["room"])
    return

readyUsers = {}

@socketio.on('setiChange')
def setiChange(data):
    if str(data['matchID']) in readyUsers:
        readyUsers.pop(data["matchID"])
        readyUsers[data["matchID"]] = []
    emit('setiChange', data, room=data['matchID'])

def checkIfReady(matchID):
    match = Match.query.get(matchID)
    if str(match.friendship.friendA) in readyUsers[str(matchID)] and str(match.friendship.friendB) in readyUsers[str(matchID)]:
        return True
    return False

# triggered when a user joins
# saves the room to session, and adds it to readyUsers if not already there
# adds user to readyUsers and makes them join the room
# checks if both opponents are present, if they are emits begin (game start)
# emits join to change the waiting for text
@socketio.on('join')
def join(data):
    match = Match.query.get(data["room"])
    session['room'] = data["room"]
    if data["room"] not in readyUsers:
        readyUsers[data["room"]] = []
    readyUsers[data["room"]].append(data["user"])
    join_room(data["room"])
    emit('join', {"readyUsers": readyUsers[data["room"]]}, room=data["room"])
    if checkIfReady(data["room"]):
        setCount = match.setCount()
        if len(match.sets) == 0 or match.sets[-1].winner != None:
            set = Set()
            set.scoreL = 0
            set.scoreW = 0
            set.match = match
            db.session.add(set)
            db.session.commit()
        emit('begin', {"score1": match.sets[-1].scoreL, "score2": match.sets[-1].scoreW, "set1": setCount[0], "set2": setCount[1]}, room=data["room"])
    print(readyUsers)

# triggered when a user disconnects
# makes the user leave the room and removes the user id from readyUsers for their room
# if room is empty, it gets deleted
# emits unjoin to change waiting for text
@socketio.on('disconnect')
def disconnect():
    room = session.get('room')
    session.pop("room")
    readyUsers[room].remove(str(current_user.id))
    emit('unjoin', {"readyUsers": readyUsers[room]}, room=room)
    leave_room(room)
    if len(readyUsers[room]) == 0:
        del readyUsers[room]

@socketio.on('changeResult')
def changeResult(data):
    emit('changeResult', room=data["matchID"])
    # return redirect(url_for('chat', matchID=match.id, unique=unique))

@app.route('/newmatch/<opponent>')
@login_required
def newMatch(opponent):
    opponent = User.query.get(opponent)

    friendship = Friendship.query.filter(or_(Friendship.friendA==current_user.id, Friendship.friendB==current_user.id), or_(Friendship.friendA==opponent.id, Friendship.friendB==opponent.id)).first()
    for i in friendship.matches:
        if i.winner == None:
            flash("Such match already exists.")
            return redirect(url_for('oneMatch', id=i.id))

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

    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('invites'))

    # m2 = Match.query.filter_by(invitee=current_user.id, inviter=opponent.id).first()
    # if (not Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first() and not m2) or (m2.started == False or Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first().started == False):
    #     return render_template('matchSettings.html', opponent=opponent, unique=unique, matchID=match.id)
    # elif m2:
    #     match = m2
    #     unique = match.unique        
    # else:
    #     match = Match.query.filter_by(inviter=current_user.id, invitee=opponent.id).first()
    #     unique = match.unique

@app.route('/acceptmatch/<inviter>')
@login_required
def acceptMatch(inviter):
    opponent = User.query.get(inviter)
    invite = Invite.query.filter(Invite.invitee==current_user.id, Invite.inviter==opponent.id).first()
    friendship = Friendship.query.filter(or_(Friendship.friendA==current_user.id, Friendship.friendB==current_user.id), or_(Friendship.friendA==opponent.id, Friendship.friendB==opponent.id)).first()

    if invite == None or current_user.id != invite.invitee:
        return redirect(url_for('index'))

    unique = generate_unique_code(10)
    matches.append(unique)
    match = Match()
    match.unique = unique
    match.finished = False
    match.setiCount = 3
    db.session.add(match)
    friendship.matches.append(match)
    db.session.delete(invite)
    db.session.commit()
    return redirect(url_for('oneMatch', id=match.id))

@app.route('/pastmatches')
@login_required
def pastmatches():
    session['url'] = url_for('pastmatches')

    d = (Match.query.filter(or_(Match.winner==current_user.id, Match.loser==current_user.id)).order_by(Match.matchDate.desc())).all()

    return render_template('pastmatches.html', user=current_user, User=User, matches=d)

@app.route('/pastmatches/sort/<what>/<type>')
@login_required
def pastmatchesSort(what, type):
    session['url'] = url_for('pastmatchesSort', what=what, type=type)
    d = Match.query.filter(or_(Match.winner==current_user.id, Match.loser==current_user.id))
    if what == "date":
        if type == "desc":
            d = d.order_by(Match.matchDate.desc())
        elif type == "incr":
            d = d.order_by(Match.matchDate)
    # elif what == "winner":
        # if type == "desc":
        #     d = d.order_by((User.query.get(Match.winner))).all()
        # elif type == "incr":
        #     d = d.order_by(Match.winner).all()
    d = d.all()
    return render_template('pastmatches.html', user=current_user, User=User, matches=d)

@app.route('/pastmatches/export')
@login_required
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
@login_required
def oneMatch(id):
    session['url'] = url_for('oneMatch', id=id)
    match = Match.query.filter(Match.id == id).first()
    if match == None:
        return redirect(url_for('index'))
    if match.finished:
        return render_template('onematch.html', user=current_user, match=match, User=User, winner=User.query.get(match.winner), loser=User.query.get(match.loser))
    u1=User.query.get(match.friendship.friendA)
    u2=User.query.get(match.friendship.friendB)
    if current_user == u1 and match.confirmA:
        return render_template('currentmatch.html', match=match, User=User, u1=u1, u2=u2, confirmable=False)
    if current_user == u2 and match.confirmB:
        return render_template('currentmatch.html', match=match, User=User, u1=u1, u2=u2, confirmable=False)
    return render_template('currentmatch.html', match=match, User=User, u1=u1, u2=u2, confirmable=True)

chats = {}

@app.route('/match/<inviteID>/chat')
@login_required
def chat(inviteID):
    session['url'] = url_for('chat', inviteID=inviteID)
    invite = Invite.query.get(inviteID)
    # check that it is indeed one of the users and that invite exists
    if (invite == None or current_user.id not in [invite.inviter, invite.invitee]):
        return redirect(url_for('index'))

    u1 = User.query.get(invite.invitee)
    u2 = User.query.get(invite.inviter)
    return render_template('chat.html', u1=u1, u2=u2, Invite=Invite, inviteID=inviteID)

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
@login_required
def invites():
    session['url'] = url_for('invites')
    invites = current_user.get_inboundInvites()
    invited = current_user.get_outboundInvites()
    return render_template('invites.html', invitesLen=len(invites), invitedLen=len(invited), invites=invites, invited=invited, Invite=Invite)

@app.route('/decline/<invite>')
@login_required
def declineInvite(invite):
    invite = Invite.query.get(invite)
    db.session.delete(invite)
    db.session.commit()
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('invites'))

@app.route('/profile/<username>/<userID>')
@login_required
def profile(username, userID):
    session['url'] = url_for('profile', username=username, userID=userID)
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
    invites = current_user.get_inboundInvites()
    if user in invites:
        return render_template('profile.html', loggedin=True, user=user, friend=True, invites=True, Invite=Invite)
    invited = current_user.get_outboundInvites()
    if user in invited:
        return render_template('profile.html', loggedin=True, user=user, friend=True, invited=True, Invite=Invite)
    return render_template('profile.html', loggedin=True, user=user, friend=True, invites=False, invited=False, Invite=Invite)

@app.route('/editprofile', methods=["GET", "POST"])
@login_required
def editProfile():
    if request.method == "GET":
        return render_template('editProfile.html')
    info = request.form
    current_user.age_group = info['age']
    current_user.experience = info['experience']
    # changing location
    prev = current_user.location
    if prev != None:
        prev.users.remove(current_user)
    loc = Location.query.filter_by(location=info['location']).first()
    if loc == None:
        loc = Location()
        loc.location = info['location']
        db.session.add(loc)
    loc.users.append(current_user)
    db.session.commit()
    return redirect(url_for('profile', username=current_user.username, userID=current_user.id))

@app.route('/editmatch/<matchID>', methods=["GET", "POST"])
@login_required
def editMatch(matchID):
    match = Match.query.get(matchID)
    if match == None:
        return redirect(url_for('index'))
    if match.finished:
        return redirect(url_for('oneMatch'), id=match.id)
    if request.method == "GET":
        locations = Location.query.order_by(Location.location).all()
        return render_template('editCurrentmatch.html', locations=locations, match=match, u1=User.query.get(match.friendship.friendA), u2=User.query.get(match.friendship.friendB))
    match.confirmA = False
    match.confirmB = False
    info = request.form
    # change location
    if info['locationDropdown'] == "Add New Location":
        loc = Location.query.filter_by(location=info['location']).first()
        if loc == None:
            loc = Location()
            loc.location = info['location']
            db.session.add(loc)
        match.location = loc
    else:
        match.location = Location.query.filter_by(location=info['locationDropdown']).first()
    match.tag
    match.notes = info['note']
    match.timeSuggestion
    db.session.commit()
    # change set results
    for i in range(match.setiCount):
        a = "setA" + str(i)
        b = "setB" + str(i)
        a = request.form[a]
        b = request.form[b]
        if a != "" or b != "":
            if a == "":
                a = match.sets[i].scoreL
            if b == "":
                b = match.sets[i].scoreW
            a = int(a)
            b = int(b)
            maxi = max(a, b)
            mini = min(a, b)
            if mini < 0:
                flash("You entered an imposible score.")
                return redirect(url_for('oneMatch', id=match.id))
            if (maxi == 11 and mini < 10) or (maxi > 11 and maxi-mini == 2):
                if len(match.sets) > i:
                    match.sets[i].scoreL = a
                    match.sets[i].scoreW = b
                    if a > b:
                        match.sets[i].winner = match.friendship.friendA
                        match.sets[i].loser = match.friendship.friendB
                    else:
                        match.sets[i].winner = match.friendship.friendB
                        match.sets[i].loser = match.friendship.friendA
                else:
                    set = Set()
                    set.scoreL = a
                    set.scoreW = b
                    set.match = match
                    if a > b:
                        set.winner = match.friendship.friendA
                        set.loser = match.friendship.friendB
                    else:
                        set.winner = match.friendship.friendB
                        set.loser = match.friendship.friendA
                    db.session.add(set)
            else:
                flash("You entered an imposible score.")
                return redirect(url_for('oneMatch', id=match.id))
    db.session.commit()
    return redirect(url_for('oneMatch', id=match.id))

@app.route('/match/<matchID>/confirmresults')
@login_required
def matchConfirm(matchID):
    match = Match.query.get(matchID)
    if len(match.sets) < match.setiCount or match.sets[match.setiCount-1].winner ==  None:
        flash("Match must have a score.")
        return redirect(url_for('oneMatch', id=match.id))
    if current_user.id == match.friendship.friendA:
        match.confirmA = True
    elif current_user.id == match.friendship.friendB:
        match.confirmB = True
    if match.confirmA and match.confirmB:
        match.finished = True
        count = match.setCount()
        if count[0] > count[1]:
            match.winner = match.friendship.friendA
            match.loser = match.friendship.friendB
        else:
            match.winner = match.friendship.friendB
            match.loser = match.friendship.friendA
    db.session.commit()
    return redirect(url_for('oneMatch', id=match.id))

@app.route('/members/<who>')
@login_required
def allusers(who):
    session['url'] = url_for('allusers', who=who)
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
    inInvites = current_user.get_inboundInvites()
    outInvites = current_user.get_outboundInvites()

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
    return render_template('allusers.html', Invite=Invite, userCount=userCount, allUsers=allUsers, loggedin=current_user.is_active, btnA=btnA, btnF=btnF, btnR=btnR, friends=friends, requested=requested, requester=requester, inInvites=inInvites, outInvites=outInvites)

@app.route('/friendrequest/<friendName>/<friendID>')
@login_required
def friendRequest(friendName, friendID):
    request = FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first()
    if request:
        flash("A friend request has already been sent.")
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('allusers', who="all"))
    friendRequest = FriendRequest(
        requester = current_user.id,
        requested = friendID)
    db.session.add(friendRequest)
    db.session.commit()
    flash("Friend request sent successfully.")
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('allusers', who="all"))

@app.route('/removerequest/<friendID>')
def removeRequest(friendID):
    if FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first():
        db.session.delete(FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first())
    else:
        db.session.delete(FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first())
    db.session.commit()
    return redirect(url_for('allusers', who="friendrequests"))

@app.route('/addfriend/<friendName>/<friendID>')
@login_required
def addFriend(friendName, friendID):
    friend = Friendship.query.filter_by(friendA=current_user.id, friendB=friendID).first()
    if friend:
        flash("You are already friends with this user.")
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('allusers', who="friends"))
    request = FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first()
    if not request:
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('allusers', who="friendrequests"))
    db.session.delete(request)
    friend = Friendship(
        friendB = current_user.id,
        friendA = friendID)
    db.session.add(friend)
    db.session.commit()
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removefriend/<friendName>/<friendID>')
@login_required
def removeFriend(friendName, friendID):
    a = (Friendship.query.filter_by(friendA=current_user.id, friendB=friendID).first())
    if not a:
        a = Friendship.query.filter_by(friendB=current_user.id, friendA=friendID).first()
    db.session.delete(a)
    db.session.commit()
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('profile', username=friendName, userID=friendID))
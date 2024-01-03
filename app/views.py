from app import app, db, socketio
from flask import render_template, request, redirect, url_for, jsonify, flash, send_file, session
from app.models import User, FriendRequest, Friendship, Match, Invite, Location, Tag, Set, Notification, login_manager
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sqlalchemy import text, update, select, or_
import random
from string import ascii_letters
from flask_socketio import join_room, leave_room, send, emit
from datetime import datetime
import csv
from werkzeug.utils import secure_filename
import os

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def createNotification(user, content, type):
    notif = Notification()
    notif.user = user
    notif.content = content
    notif.type = type
    db.session.add(notif)
    db.session.commit()
    return

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
        wins = Match.query.filter(Match.winner==current_user.id).all()
        losses = Match.query.filter(Match.loser==current_user.id).all()
        invites = current_user.get_inboundInvites()
        return render_template('loggedinHomepage.html', User=User, Invite=Invite, matches=matches, invites=invites, wins=len(wins), losses=len(losses))
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
    return render_template('notifications.html', notifications=current_user.notifications)

@app.route('/notifications/<id>/read')
@login_required
def readNotification(id):
    notif = Notification.query.get(id)
    notif.read = True
    db.session.commit()
    return redirect(url_for('notifications'))

def generate_unique_code(length):
    while True:
        code = ""
        for i in range(length):
            code += random.choice(ascii_letters)
        if Match.query.filter(Match.unique == code).first() == None:
            break
    return code

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
            set.scoreB += 1
        else:
            set.scoreA += 1
        if max(set.scoreB, set.scoreA) >= 11 and max(set.scoreB, set.scoreA) - min(set.scoreB, set.scoreA) >= 2:
            if set.scoreA > set.scoreB:
                set.winner = match.friendship.friendA
                set.loser = match.friendship.friendB
            else:
                set.loser = match.friendship.friendA
                set.winner = match.friendship.friendB
            if match.setiCount == len(match.sets):
                match.confirmA = False
                match.confirmB = False
                match.date = datetime.today()
                emit('redirect', {"url": url_for('oneMatch', id=data["room"])}, room=data["room"])
            else:
                newSet = Set()
                newSet.scoreA = 0
                newSet.scoreB = 0
                newSet.match = match
                db.session.add(newSet)
                emit('updateSet', {"to": set.winner}, room=data["room"])
            db.session.commit()
            return
    if data["what"] == "minus":
        if data["who"] == "1":
            if set.scoreB > 0:
                set.scoreB -= 1
        else:
            if set.scoreA > 0:
                set.scoreA -= 1
    emit('score', {"score1": set.scoreA, "score2": set.scoreB}, room=data["room"])
    db.session.commit()

readyUsers = {}

# @socketio.on('setiChange')
# def setiChange(data):
#     if str(data['matchID']) in readyUsers:
#         readyUsers.pop(data["matchID"])
#         readyUsers[data["matchID"]] = []
#     emit('setiChange', data, room=data['matchID'])

def checkIfReady(matchID):
    match = Match.query.get(matchID)
    if str(match.friendship.friendA) in readyUsers[str(matchID)] and str(match.friendship.friendB) in readyUsers[str(matchID)]:
        return True
    return False

# triggered when a user joins
@socketio.on('join')
def join(data):
    # the row in the Match table associated with current match; data["room"] is the match's id
    match = Match.query.get(data["room"])
    # saves the room to session, and adds it to readyUsers if not already there
    session['room'] = data["room"]
    # adds user to readyUsers
    if data["room"] not in readyUsers:
        readyUsers[data["room"]] = []
    readyUsers[data["room"]].append(data["user"])
    # joins user to the room
    join_room(data["room"])
    # tells other spectators that the user has joined
    emit('join', {"readyUsers": readyUsers[data["room"]]}, room=data["room"])
    # checks if both opponents are present, if they are emits begin (game start)
    if checkIfReady(data["room"]):
        setCount = match.setCount()
        # if an ongoing set doesn't exist, create new set
        if len(match.sets) == 0 or match.sets[-1].winner != None:
            set = Set()
            set.scoreA = 0
            set.scoreB = 0
            set.match = match
            db.session.add(set)
            db.session.commit()
        emit('begin', {"score1": match.sets[-1].scoreA, "score2": match.sets[-1].scoreB, "set1": setCount[0], "set2": setCount[1]}, room=data["room"])

# triggered when a user disconnects
@socketio.on('disconnect')
def disconnect():
    room = session.get('room')
    session.pop("room")
    # removes the user id from readyUsers for their room
    readyUsers[room].remove(str(current_user.id))
    # tells other users who is still present
    emit('unjoin', {"readyUsers": readyUsers[room]}, room=room)
    # makes the user leave the room
    leave_room(room)
    # if room is empty, it gets deleted
    if len(readyUsers[room]) == 0:
        del readyUsers[room]

# @socketio.on('changeResult')
# def changeResult(data):
#     emit('changeResult', room=data["matchID"])
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

    createNotification(opponent, current_user.username + " has invited you to a match.", "inv")

    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('invites'))

# accepts a match request
# deletes the invite and creates a new match
@app.route('/acceptmatch/<inviter>')
@login_required
def acceptMatch(inviter):
    # current_user is the invitee, so the inviter is current_user's opponent
    opponent = User.query.get(inviter)
    # the invite that is to be accepted
    invite = Invite.query.filter(Invite.invitee==current_user.id, Invite.inviter==opponent.id).first()

    # if such an invite doesn't exist or current_user is not its recipient (invitee) the invite shouldn't be accepted so the user is redirected to the homepage/landing page
    if invite == None or current_user.id != invite.invitee:
        return redirect(url_for('index'))

    # the friendship between the current_user and opponent i.e. the inviter and invitee
    friendship = Friendship.query.filter(or_(Friendship.friendA==current_user.id, Friendship.friendB==current_user.id), or_(Friendship.friendA==opponent.id, Friendship.friendB==opponent.id)).first()

    # create a match
    match = Match()
    unique = generate_unique_code(10)
    match.unique = unique
    match.finished = False
    match.setiCount = 3
    match.location = Location.query.filter(Location.location == "None").first()
    match.tag = Tag.query.filter(Tag.tag == "Untagged").first()
    db.session.add(match)
    # connect the match to the friendship
    friendship.matches.append(match)
    # delete the invite
    db.session.delete(invite)
    db.session.commit()

    # notify the opponent (inviter) that the match invite has been accepted
    createNotification(opponent, current_user.username + " has accepted your match invite.", "inv")

    # return current_user to the url they came from or if it is not stored in session, to the match they have just accepted
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('oneMatch', id=match.id))

@app.route('/pastmatches')
@login_required
def pastmatches():
    session['url'] = url_for('pastmatches')

    d = (Match.query.filter(or_(Match.winner==current_user.id, Match.loser==current_user.id)).order_by(Match.date.desc())).all()

    return render_template('pastmatches.html', user=current_user, User=User, matches=d)

@app.route('/pastmatches/sort/<what>/<type>')
@login_required
def pastmatchesSort(what, type):
    session['url'] = url_for('pastmatchesSort', what=what, type=type)
    d = Match.query.filter(or_(Match.winner==current_user.id, Match.loser==current_user.id))
    if what == "date":
        if type == "desc":
            d = d.order_by(Match.date.desc())
        elif type == "incr":
            d = d.order_by(Match.date)
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
    matches = Match.query.filter(or_(Match.winner == current_user.id, Match.loser == current_user.id)).all()
    print(matches)
    with open('export.csv', 'w', newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["winner", "loser", "notes", "date", "setiCount", "location", "tag"])
        writer.writerow(["scoreA", "scoreB", "winner", "loser"])
        for m in matches:
            writer.writerow([m.winner, m.loser, m.notes, m.date, m.setiCount, m.location.id, m.tag.id])
            for s in m.sets:
                writer.writerow([s.scoreA, s.scoreB, s.winner, s.loser])

    fName = current_user.username + 'PingPongerExport.csv'
    return send_file('../export.csv', mimetype='type/csv', download_name=fName, as_attachment=True)

ALLOWED_EXTENSIONS = {'csv'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/pastmatches/import', methods=['POST'])
@login_required
def importMatch():
    if 'file' not in request.files:
        flash('No file part')
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('pastmatches'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('pastmatches'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        with open(filepath, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            next(reader)
            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                match = Match()
                match.finished = True
                match.unique = generate_unique_code(10)
                match.winner = int(row[0])
                match.loser = int(row[1])
                match.notes = row[2]
                # match.date = (row[3])
                match.setiCount = int(row[4])
                match.location = Location.query.get(row[5])
                match.tag = Tag.query.get(row[6])
                friendship = Friendship.query.filter(or_(Friendship.friendA==match.winner, Friendship.friendB==match.winner), or_(Friendship.friendA==match.loser, Friendship.friendB==match.loser)).first()
                match.friendship = friendship
                db.session.add(match)
                for i in range(int(row[4])):
                    curSet = next(reader)
                    nSet = Set()
                    nSet.scoreA = int(curSet[0])
                    nSet.scoreB = int(curSet[1])
                    nSet.winner = int(curSet[2])
                    nSet.loser = int(curSet[3])
                    nSet.match = match
                    db.session.add(nSet)
                db.session.commit()
        os.remove(filepath)
    else:
        flash('Only CSV files can be uploaded.')
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('pastmatches'))
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('pastmatches'))
    # fName = current_user.username + 'PingPongerExport.csv'
    # return send_file('../export.csv', mimetype='type/csv', download_name=fName, as_attachment=True)

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
    if not invite:
        if 'url' in session:
            return redirect(session['url'])
        return redirect(url_for('index'))
    createNotification(User.query.get(invite.inviter), User.query.get(invite.invitee).username + " has declined your invite to a match.", "inv")
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
    if info['location'] != "":
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
        return redirect(url_for('oneMatch', id=match.id))
    if request.method == "GET":
        locations = Location.query.order_by(Location.location).all()
        tags = Tag.query.order_by(Tag.tag).all()
        return render_template('editCurrentmatch.html', locations=locations, tags=tags, match=match, u1=User.query.get(match.friendship.friendA), u2=User.query.get(match.friendship.friendB))
    match.confirmA = False
    match.confirmB = False
    info = request.form
    # change location
    if info['location'] != "":
        loc = Location.query.filter_by(location=info['location']).first()
        if not loc:
            loc = Location()
            loc.location = info['location']
            db.session.add(loc)
        match.location = loc
    if info['tag'] != "":
        tag = Tag.query.filter_by(tag=info['tag']).first()
        if not tag:
            tag = Tag()
            tag.tag = info['tag']
            db.session.add(tag)
        match.tag = tag
    match.notes = info['note']
    date = info['date']
    time = info['time']
    if info['time'] == "":
        time = datetime.today().strftime('%H:%M')
    if info['date'] == "":
        date = datetime.today().strftime('%Y-%m-%d')
    match.date = datetime.strptime(date + " " + time,"%Y-%m-%d %H:%M")
    db.session.commit()
    if current_user == match.friendship.friendA:
        createNotification(User.query.get(match.friendship.friendB), current_user.username + " has edited your current match data.", "mat")
    if current_user == match.friendship.friendB:
        createNotification(User.query.get(match.friendship.friendA), current_user.username + " has edited your current match data.", "mat")
    # change set results
    for i in range(match.setiCount):
        a = "setA" + str(i)
        b = "setB" + str(i)
        a = request.form[a]
        b = request.form[b]
        if a != "" or b != "":
            if a == "":
                a = match.sets[i].scoreA
            if b == "":
                b = match.sets[i].scoreB
            a = int(a)
            b = int(b)
            maxi = max(a, b)
            mini = min(a, b)
            if mini < 0:
                flash("You entered an imposible score.")
                return redirect(url_for('oneMatch', id=match.id))
            if (maxi == 11 and mini < 10) or (maxi > 11 and maxi-mini == 2):
                if len(match.sets) > i:
                    match.sets[i].scoreA = a
                    match.sets[i].scoreB = b
                    if a > b:
                        match.sets[i].winner = match.friendship.friendA
                        match.sets[i].loser = match.friendship.friendB
                    else:
                        match.sets[i].winner = match.friendship.friendB
                        match.sets[i].loser = match.friendship.friendA
                else:
                    set = Set()
                    set.scoreA = a
                    set.scoreB = b
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
        createNotification(User.query.get(match.friendship.friendB), current_user.username + " has confirmed your match results.", "mat")
    elif current_user.id == match.friendship.friendB:
        match.confirmB = True
        createNotification(User.query.get(match.friendship.friendA), current_user.username + " has confirmed your match results.", "mat")
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

@app.route('/statistics')
@login_required
def statistics():
    scores = []
    labels = []
    sets = Set.query.filter(or_(Set.winner==current_user.id, Set.loser==current_user.id)).all()
    for i in sets:
        if i.winner == current_user.id:
            scores.append(max(i.scoreA, i.scoreB))
            labels.append(User.query.get(i.loser).username)
        else:
            scores.append(min(i.scoreA, i.scoreB))
            labels.append(User.query.get(i.winner).username)
    wins = Match.query.filter(Match.winner==current_user.id).all()
    losses = Match.query.filter(Match.loser==current_user.id).all()

    return render_template('statistics.html', scores=scores, lables=labels, wins=len(wins), losses=len(losses))

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
    createNotification(User.query.get(friendID), current_user.username + " has sent you a friend request.", "fri")
    flash("Friend request sent successfully.")
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('allusers', who="all"))

@app.route('/removerequest/<friendID>')
def removeRequest(friendID):
    req = FriendRequest.query.filter_by(requester=current_user.id, requested=friendID).first()
    if req:
        db.session.delete(req)
    else:
        req = FriendRequest.query.filter_by(requested=current_user.id, requester=friendID).first()
        if req:
            db.session.delete(req)
            createNotification(User.query.get(friendID), current_user.username + " has rejected your friend request.", "fri")
    db.session.commit()
    if 'url' in session:
        return redirect(session['url'])
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
    createNotification(User.query.get(friendID), current_user.username + " has accepted your friend request.", "fri")
    return redirect(url_for('profile', username=friendName, userID=friendID))

@app.route('/removefriend/<friendName>/<friendID>')
@login_required
def removeFriend(friendName, friendID):
    a = (Friendship.query.filter_by(friendA=current_user.id, friendB=friendID).first())
    if not a:
        a = Friendship.query.filter_by(friendB=current_user.id, friendA=friendID).first()
    db.session.delete(a)
    db.session.commit()
    createNotification(User.query.get(friendID), current_user.username + " has terminated your friendship.", "fri")
    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('profile', username=friendName, userID=friendID))
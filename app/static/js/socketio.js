 document.addEventListener('DOMContentLoaded', () => {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    var readyUsers;

    socket.on('connect', () => {
        socket.emit('join', {"room": matchID})
    });

    socket.on('start', data => {
        if (data.user == u1) {
            document.querySelector("#u1").innerHTML = data.user + " is ready."
        }
        else {
            document.querySelector("#u2").innerHTML = data.user + " is ready."
        }
        if (data.ready) {
            document.querySelector("#u1").innerHTML = u1
            document.querySelector("#u2").innerHTML = u2
            document.querySelector('#u1score').innerHTML = 0
            document.querySelector('#u2score').innerHTML = 0
            document.querySelector('#u1scoreSet').innerHTML = 0
            document.querySelector('#u2scoreSet').innerHTML = 0
            starter = data.starter
            document.querySelector('#turn'+starter).style.visibility = "visible"
            turn = starter
            notstarter = "1"
            if (starter == "1") {
                notstarter = "2"
            }
            serva = 0
        }
    });
    
    socket.on('score', data => {
        serva = data.serva
        turn = data.turn
        document.querySelector('#u1score').innerHTML = data[0]
        document.querySelector('#u2score').innerHTML = data[1]
        if (turn == starter) {
            document.querySelector('#turn'+notstarter).style.visibility = "hidden"
            document.querySelector('#turn'+starter).style.visibility = "visible"
        }
        else {
            document.querySelector('#turn'+starter).style.visibility = "hidden"
            document.querySelector('#turn'+notstarter).style.visibility = "visible"
        }
    });

    socket.on('gameOver', data => {
        if (data["winner"] == "0") {
            winner = u1
        }
        else if (data["winner"] == "1") {
            winner = u2
        }
        document.querySelector('#isactive').innerHTML = winner + " won."
    })

    document.querySelector('#addU1').onclick = () => {
        socket.emit('score', {"who": "0", "what": "plus", "serva":serva, "turn":turn, "starter":starter, "notstarter":notstarter, "room":matchID, "0": parseInt(document.querySelector('#u1score').innerHTML), "1": parseInt(document.querySelector('#u2score').innerHTML)});
    };
    document.querySelector('#addU2').onclick = () => {
        socket.emit('score', {"who": "1", "what": "plus", "serva":serva, "turn":turn, "starter":starter, "notstarter":notstarter, "room":matchID, "0": parseInt(document.querySelector('#u1score').innerHTML), "1": parseInt(document.querySelector('#u2score').innerHTML)});
    };
    document.querySelector('#subtractU1').onclick = () => {
        socket.emit('score', {"who": "0", "what": "minus", "serva":serva, "turn":turn, "starter":starter, "notstarter":notstarter, "room":matchID, "0": parseInt(document.querySelector('#u1score').innerHTML), "1": parseInt(document.querySelector('#u2score').innerHTML)});
    };
    document.querySelector('#subtractU2').onclick = () => {
        socket.emit('score', {"who": "1", "what": "minus", "serva":serva, "turn":turn, "starter":starter, "notstarter":notstarter, "room":matchID, "0": parseInt(document.querySelector('#u1score').innerHTML), "1": parseInt(document.querySelector('#u2score').innerHTML)});
    };
    
    document.querySelector('#gumb').onclick = () => {
        socket.emit('start', {"user":current_user, "matchID":matchID});
    };
});
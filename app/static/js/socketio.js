 document.addEventListener('DOMContentLoaded', () => {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    socket.on('connect', () => {
        socket.emit('join', {"room": matchID})
    });

    socket.on('setiChange', data => {
        document.querySelector('#gumb').style.visibility = "visible";
        document.querySelector("#seti").value = data.seti
        document.querySelector("#u1").innerHTML = u1
        document.querySelector("#u2").innerHTML = u2
    })

    socket.on('leave', () => {
        socket.emit('leave', {"room": matchID, "user":current_user})
        document.querySelector("#top").innerHTML = `<h1>Results confirmed and saved.</h1>`
        document.querySelector('#u1scoreSet').style.display = "none"
        document.querySelector('#u2scoreSet').style.display = "none"
        document.querySelector("#u1").style.display = "none"
        document.querySelector("#u2").style.display = "none"
        document.querySelector("#iks").style.visibility = "hidden"
    })

    socket.on('stopWait', () => {
        waiting = false
    })

    socket.on('start', data => {
        if (data.ready == false) {
            if (data.user == u1) {
                document.querySelector("#u1").innerHTML = data.user + " is ready."
            }
            else {
                document.querySelector("#u2").innerHTML = data.user + " is ready."
            }
        }
        else {
            document.querySelector("#u1").innerHTML = u1
            document.querySelector("#u2").innerHTML = u2
            document.querySelector('#u1score').innerHTML = 0
            document.querySelector('#u2score').innerHTML = 0
            document.querySelector('#u1scoreSet').innerHTML = 0
            document.querySelector('#u2scoreSet').innerHTML = 0
            document.querySelector('#addU1').style.display = "block"
            document.querySelector('#addU2').style.display = "block"
            document.querySelector('#subtractU1').style.display = "block"
            document.querySelector('#subtractU2').style.display = "block"
            document.querySelector('#addsetU1').style.display = "block"
            document.querySelector('#addsetU2').style.display = "block"
            document.querySelector('#subtractsetU1').style.display = "block"
            document.querySelector('#subtractsetU2').style.display = "block"
            document.querySelector('#gumb').style.display = "none"
            document.querySelector('#settingsi').style.display = "none"
            starter = data.starter
            document.querySelector('#turn'+starter).style.visibility = "visible"
            turn = starter
            notstarter = "1"
            if (starter == "1") {
                notstarter = "2"
            }
            serva = 0
            u1points = 0
            u2points = 0
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

    socket.on('setiMinus', data => {
        serva = data.serva
        document.querySelector('#u1scoreSet').innerHTML = data[0]
        document.querySelector('#u2scoreSet').innerHTML = data[1]
        document.querySelector('#u1score').innerHTML = 0
        document.querySelector('#u2score').innerHTML = 0
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
        serva = data.serva
        if (starter == "1") {
            notstarter = "1"
            starter = "2"
        }
        else {
            starter = "1"
            notstarter = "2"
        }
        turn = starter
        document.querySelector('#turn'+notstarter).style.visibility = "hidden"
        document.querySelector('#turn'+starter).style.visibility = "visible"
        if (data["winner"] == "0") {
            document.querySelector('#u1scoreSet').innerHTML = parseInt(document.querySelector("#u1scoreSet").innerHTML) + 1
        }
        else if (data["winner"] == "1") {
            document.querySelector("#u2scoreSet").innerHTML = parseInt(document.querySelector("#u2scoreSet").innerHTML) + 1
        }
        u1points += document.querySelector('#u1score').innerHTML
        u2points += document.querySelector('#u2score').innerHTML
        document.querySelector('#u1score').innerHTML = 0
        document.querySelector('#u2score').innerHTML = 0
        if (parseInt(document.querySelector("#u1scoreSet").innerHTML) + parseInt(document.querySelector("#u2scoreSet").innerHTML) == document.getElementById("seti").value) {
            document.querySelector("#top").style.display = "block"
            if (parseInt(document.querySelector("#u1scoreSet").innerHTML) > parseInt(document.querySelector("#u2scoreSet").innerHTML)) {
                winner = u1
                loser = u2
                winP = u1points
                losP = u2points
            }
            else {
                winner = u2
                loser = u1
                winP = u2points
                losP = u1points
            }
            if (winner == u1) {
                if (u1 == current_user) {
                    m = "Congradulations, " + u1 + "! You have won."
                }
                else {
                    m = u1 + " has won. Better luck next time."
                }
                setRez = document.querySelector("#u1scoreSet").innerHTML + document.querySelector("#u2scoreSet").innerHTML
            }
            else {
                if (u2 == current_user) {
                    m = "Congradulations, " + u2 + "! You have won."
                }
                else {
                    m = u2 + " has won. Better luck next time."
                }
                setRez = document.querySelector("#u2scoreSet").innerHTML + document.querySelector("#u1scoreSet").innerHTML
            }
            document.querySelector("#top").innerHTML = `<h1>${m}</h1>`
            document.querySelector('#addU1').style.display = "none"
            document.querySelector('#addU2').style.display = "none"
            document.querySelector('#subtractU1').style.display = "none"
            document.querySelector('#subtractU2').style.display = "none"
            document.querySelector('#addsetU1').style.display = "none"
            document.querySelector('#addsetU2').style.display = "none"
            document.querySelector('#subtractsetU1').style.display = "none"
            document.querySelector('#subtractsetU2').style.display = "none"
            document.querySelector('#u1score').style.display = "none"
            document.querySelector('#u2score').style.display = "none"
            document.querySelector('#turn1').style.visibility = "hidden"
            document.querySelector('#turn2').style.visibility = "hidden"
            document.querySelector('#confirm').style.display = "block"
            waiting = true
        }
    })

    socket.on('changeResult', data => {
        document.querySelector('#addsetU1').style.display = "block"
        document.querySelector('#addsetU2').style.display = "block"
        document.querySelector('#subtractsetU1').style.display = "block"
        document.querySelector('#subtractsetU2').style.display = "block"
        document.querySelector('#confirm').style.display = "none"
        document.querySelector('#u1score').innerHTML = 0
        document.querySelector('#u2score').innerHTML = 0
        if (document.querySelector('#u1scoreSet').innerHTML == document.querySelector("#seti").value) {
            document.querySelector('#u1scoreSet').innerHTML -= 1
        }
        else {
            document.querySelector('#u2scoreSet').innerHTML -= 1
        }
        waiting = true
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

    document.querySelector('#addsetU1').onclick = () => {
        socket.emit('setAdjust', {"who": "0", "what": "plus", "room":matchID, "0": parseInt(document.querySelector('#u1scoreSet').innerHTML), "1": parseInt(document.querySelector('#u2scoreSet').innerHTML)});
    };
    document.querySelector('#addsetU2').onclick = () => {
        socket.emit('setAdjust', {"who": "1", "what": "plus", "room":matchID, "0": parseInt(document.querySelector('#u1scoreSet').innerHTML), "1": parseInt(document.querySelector('#u2scoreSet').innerHTML)});
    };
    document.querySelector('#subtractsetU1').onclick = () => {
        socket.emit('setAdjust', {"who": "0", "what": "minus", "room":matchID, "0": parseInt(document.querySelector('#u1scoreSet').innerHTML), "1": parseInt(document.querySelector('#u2scoreSet').innerHTML)});
    };
    document.querySelector('#subtractsetU2').onclick = () => {
        socket.emit('setAdjust', {"who": "1", "what": "minus", "room":matchID, "0": parseInt(document.querySelector('#u1scoreSet').innerHTML), "1": parseInt(document.querySelector('#u2scoreSet').innerHTML)});
    };
    
    document.querySelector('#gumb').onclick = () => {
        document.querySelector('#gumb').style.visibility = "hidden";
        socket.emit('start', {"user":current_user, "matchID":matchID});
    };

    document.querySelector("#seti").addEventListener("change", function() {
        socket.emit('setiChange', {"matchID":matchID, "seti":document.getElementById("seti").value})
    })

    document.querySelector('#declineConfirm').onclick = () => {
        socket.emit('changeResult', {"matchID":matchID})
    }

    document.querySelector('#confirmResult').onclick = () => {
        document.querySelector('#confirmResult').style.display = "none"
        document.querySelector('#declineConfirm').style.display = "none"
        document.querySelector("#top").innerHTML = `<h1>Waiting for your opponent to confirm the results...</h1>`
        socket.emit('save', {"matchID":matchID, "winner":winner, "loser":loser, "seti":document.getElementById("seti").value, "setRez":setRez, "winP":winP, "losP":losP, "waiting":waiting, "room":matchID})
    }
});
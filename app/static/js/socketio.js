 document.addEventListener('DOMContentLoaded', () => {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    socket.on('connect', () => {
        socket.emit('join', {"room": matchID, "user": current_user})
    });

    // handles the "waiting" text
    socket.on('join', data => {
        if (data["readyUsers"].includes(u1)) {
            document.querySelector("#u1").innerHTML = `<h1>`+ u1name + `</h1>`
        }
        if (data["readyUsers"].includes(u2)) {
            document.querySelector("#u2").innerHTML = `<h1>`+ u2name + `</h1>`
        }
    })

    // handles the "waiting" text
    socket.on('unjoin', data => {
        if (data["readyUsers"].includes(u1) == false) {
            document.querySelector("#u1").innerHTML = `<h1>Waiting for ` + u1name + `...</h1>`
        }
        if (data["readyUsers"].includes(u2) == false) {
            document.querySelector("#u2").innerHTML = `<h1>Waiting for ` + u2name + `...</h1>`
        }
        document.querySelector('#addU1').disabled = true
        document.querySelector('#addU2').disabled = true
        document.querySelector('#subtractU1').disabled = true
        document.querySelector('#subtractU2').disabled = true
        document.querySelector('#addsetU1').disabled = true
        document.querySelector('#addsetU2').disabled = true
        document.querySelector('#subtractsetU1').disabled = true
        document.querySelector('#subtractsetU2').disabled = true
    })
    
    // socket.on('disconnect', () => {
    //     console.log('torej to se pokaze')
    //     socket.emit('leave', {"room": matchID, "user": current_user})
    //     // document.querySelector("#top").innerHTML = `<h1>Results confirmed and saved.</h1>`
    //     // document.querySelector('#u1scoreSet').style.display = "none"
    //     // document.querySelector('#u2scoreSet').style.display = "none"
    //     // document.querySelector("#u1").style.display = "none"
    //     // document.querySelector("#u2").style.display = "none"
    //     // document.querySelector("#iks").style.visibility = "hidden"
    // })

    // with both users there, the match begins
    socket.on('begin', data => {
        document.querySelector('#u1score').innerHTML = data.score1
        document.querySelector('#u2score').innerHTML = data.score2
        document.querySelector('#u1scoreSet').innerHTML = data.set1
        document.querySelector('#u2scoreSet').innerHTML = data.set2
        document.querySelector('#addU1').style.display = "block"
        document.querySelector('#addU2').style.display = "block"
        document.querySelector('#subtractU1').style.display = "block"
        document.querySelector('#subtractU2').style.display = "block"
        document.querySelector('#addsetU1').style.display = "block"
        document.querySelector('#addsetU2').style.display = "block"
        document.querySelector('#subtractsetU1').style.display = "block"
        document.querySelector('#subtractsetU2').style.display = "block"
        document.querySelector('#addU1').disabled = false
        document.querySelector('#addU2').disabled = false
        document.querySelector('#subtractU1').disabled = false
        document.querySelector('#subtractU2').disabled = false
        document.querySelector('#addsetU1').disabled = false
        document.querySelector('#addsetU2').disabled = false
        document.querySelector('#subtractsetU1').disabled = false
        document.querySelector('#subtractsetU2').disabled = false
        document.querySelector('#turn1').style.visibility = "visible"
        turn = "1"
        serva = 0
        u1points = 0
        u2points = 0
    })

    socket.on('redirect', data => {
        window.location = data.url
    })
    
    socket.on('score', data => {
        // serva = data.serva
        // turn = data.turn
        document.querySelector('#u1score').innerHTML = data.score1
        document.querySelector('#u2score').innerHTML = data.score2
        // if (turn == starter) {
            //     document.querySelector('#turn'+notstarter).style.visibility = "hidden"
            //     document.querySelector('#turn'+starter).style.visibility = "visible"
            // }
        // else {
        //     document.querySelector('#turn'+starter).style.visibility = "hidden"
        //     document.querySelector('#turn'+notstarter).style.visibility = "visible"
        // }
    });
    
    socket.on('updateSet', data => {
        document.querySelector("#u1score").innerHTML = 0
        document.querySelector("#u2score").innerHTML = 0
        var a;
        if (data.to == u1) {
            a = document.querySelector("#u1scoreSet").innerHTML
            document.querySelector("#u1scoreSet").innerHTML = parseInt(a) + 1
        }
        else {
            a = document.querySelector("#u2scoreSet").innerHTML
            document.querySelector("#u2scoreSet").innerHTML = parseInt(a) + 1
        }
    })

    function confirmation(data) {
        if (data.user == current_user) {
            if (parseInt(data["u1score"]) + parseInt(data["u2score"] != parseInt(data["setiCount"])))
            {
                console.log(`sir do math`)
            }
            if (confirm(data["winner"] + " won! Result: " + data["u1score"] + ":" + data["u2score"])) {
                socket.emit('finalize', {"user": current_user, "what": "ok", "room": matchID})
                document.querySelector("#top").innerHTML = `<h1>Waiting for opponent to confirm the results...</h1>`
                document.querySelector('#turn1').style.visibility = "visible"
                document.querySelector('#turn2').style.visibility = "visible"
                document.querySelector('#addU1').style.display = "none"
                document.querySelector('#addU2').style.display = "none"
                document.querySelector('#subtractU1').style.display = "none"
                document.querySelector('#subtractU2').style.display = "none"
                document.querySelector('#u1score').style.display = "none"
                document.querySelector('#u2score').style.display = "none"
                document.querySelector('#turn1').style.visibility = "hidden"
                document.querySelector('#turn2').style.visibility = "hidden"
                // document.querySelector('#confirm').style.display = "block"
            }
            else {
                let result = parseInt(prompt("Please enter " + u1name + "'s score:", data["u1score"]));
                if (result == null || Number.isInteger(result) == false) {
                    confirmation(data);
                }
                else {
                    let result2 = parseInt(prompt("Please enter " + u2name + "'s score:", data["u2score"]));
                    if (result2 == null || Number.isInteger(result2) == false) {
                        confirmation(data);
                    }
                    else {
                        socket.emit('finalize', {"user": current_user, "what": "change", "u1score": result, "u2score": result2, "setiCount": data.setiCount, "room": matchID})
                    }
                }
            }
        }
    }

    socket.on('confirm', data => {
        confirmation(data)
    })

    document.querySelector('#addU1').onclick = () => {
        socket.emit('score', {"who": "0", "what": "plus", "room":matchID});
    };
    document.querySelector('#addU2').onclick = () => {
        socket.emit('score', {"who": "1", "what": "plus", "room":matchID});
    };
    document.querySelector('#subtractU1').onclick = () => {
        socket.emit('score', {"who": "0", "what": "minus", "room":matchID});
    };
    document.querySelector('#subtractU2').onclick = () => {
        socket.emit('score', {"who": "1", "what": "minus", "room":matchID});
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

    document.querySelector("#seti").addEventListener("change", function() {
        socket.emit('setiChange', {"matchID":matchID, "seti":document.getElementById("seti").value})
    })

    // document.querySelector('#declineConfirm').onclick = () => {
    //     socket.emit('changeResult', {"matchID":matchID})
    // }

    // document.querySelector('#confirmResult').onclick = () => {
    //     document.querySelector('#confirmResult').style.display = "none"
    //     document.querySelector('#declineConfirm').style.display = "none"
    //     document.querySelector("#top").innerHTML = `<h1>Waiting for your opponent to confirm the results...</h1>`
    //     socket.emit('save', {"matchID":matchID, "winner":winner, "loser":loser, "seti":document.getElementById("seti").value, "setRez":setRez, "winP":winP, "losP":losP, "waiting":waiting, "room":matchID})
    // }
});
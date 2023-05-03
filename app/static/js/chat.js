document.addEventListener('DOMContentLoaded', () => {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    const messages = document.getElementById("messages");

    const createMessage = (name, msg) => {
        document.getElementById("el").id = null
      const content = `
      <div class="text" id="el">
          <span>
              <strong>${name}</strong>: ${msg}
          </span>
          <span class="muted">
              ${new Date().toLocaleString()}
          </span>
      </div>
      `;
      messages.innerHTML += content;
      document.getElementById("el").scrollIntoView()
    };

    socket.on('connect', () => {
        socket.emit('joinChat', {"name": current_user, "room": -matchID})
    });

    socket.on('disconnect', () => {
        socket.emit('leaveChat', {"name": current_user, "room": -matchID})
    });

    socket.on("message", (data) => {
        createMessage(data.name, data.message);
    });

    document.querySelector("#send-btn").onclick = () => {
        socket.send({"room":-matchID, "message":document.getElementById("message").value, "who":current_user})
        document.getElementById("message").value = null
    }

    document.querySelector("#send-btn").onclick = () => {
        socket.send({"room":-matchID, "message":document.getElementById("message").value, "who":current_user})
        document.getElementById("message").value = null
    }

    document.querySelector("#message").addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
          document.getElementById("send-btn").click();
        }
    });
});
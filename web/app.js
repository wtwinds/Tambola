const WS_URL = "wss://tambola-f6di.onrender.com";
const socket = new WebSocket(WS_URL);

let isHost = false;
let gameMode = "AUTO";
let currentNumber = null;

/* ================= SCREEN HELPER ================= */
function showScreen(id){
  document.querySelectorAll(".screen").forEach(s =>
    s.classList.remove("active")
  );
  document.getElementById(id).classList.add("active");
}

/* ================= TICKET ================= */
function renderTicket(ticket){
  const div = document.getElementById("ticket");
  div.innerHTML = "";

  ticket.forEach(row=>{
    const r = document.createElement("div");
    r.className = "ticket-row";

    row.forEach(n=>{
      const c = document.createElement("div");
      if(n === 0){
        c.className = "ticket-cell empty";
        c.innerHTML = "&nbsp;";
      } else {
        c.className = "ticket-cell";
        c.innerText = n;
        c.onclick = () => {
          if(gameMode !== "MANUAL") return;
          if(currentNumber === null) return;
          if(Number(c.innerText) !== currentNumber) return;
          c.classList.add("marked");
        };
      }
      r.appendChild(c);
    });
    div.appendChild(r);
  });
}

/* ================= SOCKET ================= */
socket.onmessage = e => {
  const { type, data } = JSON.parse(e.data);

  if(type === "ROOM_CREATED"){
    isHost = true;
    document.getElementById("room-id").innerText = data.room_id;
    document.getElementById("start-game-btn").style.display = "block";
    showScreen("waiting-screen");
  }

  if(type === "PLAYERS_UPDATE"){
    const ul = document.getElementById("players-list");
    ul.innerHTML = "";
    data.players.forEach(p=>{
      const li = document.createElement("li");
      li.innerText = p;
      ul.appendChild(li);
    });
  }

  if(type === "TICKET_ASSIGNED"){
    renderTicket(data.ticket);
  }

  if(type === "GAME_STARTED"){
    if(data && data.mode) gameMode = data.mode;
    showScreen("game-screen");

    if(isHost){
      document.getElementById("draw-btn").style.display = "block";
    }
  }

  if(type === "NUMBER_DRAWN"){
    document.getElementById("current-number").innerText = data.number;
    currentNumber = data.number;

    if(gameMode === "AUTO"){
      document.querySelectorAll(".ticket-cell").forEach(c=>{
        if(Number(c.innerText) === data.number){
          c.classList.add("marked");
        }
      });
    }
  }
};


document.getElementById("create-room-btn").onclick = () => {
  const name = document.getElementById("player-name").value.trim();
  const mode = document.querySelector('input[name="mode"]:checked').value;
  if(!name) return;

  gameMode = mode;
  socket.send(JSON.stringify({
    type: "CREATE_ROOM",
    data: { player_name: name, mode }
  }));
};

document.getElementById("join-room-btn").onclick = () => {
  const name = document.getElementById("player-name").value.trim();
  const room = document.getElementById("room-input").value.trim();
  if(!name || !room) return;

  socket.send(JSON.stringify({
    type: "JOIN_ROOM",
    data: { player_name: name, room_id: room }
  }));

  document.getElementById("start-game-btn").style.display = "none"; // ❌ non-host
  showScreen("waiting-screen");
};

document.getElementById("start-game-btn").onclick = () => {
  if(!isHost) return;
  socket.send(JSON.stringify({ type: "START_GAME" }));
};

document.getElementById("draw-btn").onclick = () =>
  socket.send(JSON.stringify({ type: "DRAW_NUMBER" }));

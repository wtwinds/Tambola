const WS_URL = "wss://tambola-f6di.onrender.com";
const socket = new WebSocket(WS_URL);

let isHost = false;
let gameStarted = false;
let gameMode = "AUTO";
let currentNumber = null;
let drawnNumbers = [];

/* ================= SCREEN ================= */
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

/* ================= CLAIM ================= */
function claim(type){
  if(!gameStarted) return;
  socket.send(JSON.stringify({
    type: "MAKE_CLAIM",
    data: { claim: type }
  }));
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
    gameStarted = true;
    gameMode = data.mode;
    showScreen("game-screen");
    if(isHost){
      document.getElementById("draw-btn").style.display = "block";
    }
  }

  if(type === "NUMBER_DRAWN"){
    currentNumber = data.number;
    document.getElementById("current-number").innerText = data.number;

    if(!drawnNumbers.includes(data.number)){
      drawnNumbers.push(data.number);
    }

    const box = document.getElementById("drawn-numbers");
    box.innerHTML = "";
    drawnNumbers.forEach(n=>{
      const d = document.createElement("div");
      d.className = "drawn-number";
      d.innerText = n;
      box.appendChild(d);
    });

    if(gameMode === "AUTO"){
      document.querySelectorAll(".ticket-cell").forEach(c=>{
        if(Number(c.innerText) === data.number){
          c.classList.add("marked");
        }
      });
    }
  }

  if(type === "CLAIM_RESULT"){
    const box = document.getElementById("claim-status");
    box.className = "claim-status show";

    if(data.status === "SUCCESS"){
      box.classList.add("success");
      box.innerText = `${data.claim} WON by ${data.player}`;

      const claimMap = {
        "Quick 5": "QUICK_5",
        "Four Corners": "FOUR_CORNERS",
        "1st Line": "FIRST_LINE",
        "2nd Line": "SECOND_LINE",
        "3rd Line": "THIRD_LINE",
        "Tambola": "TAMBOLA"
      };

      document.querySelectorAll(".claims button").forEach(btn=>{
        if(claimMap[btn.innerText] === data.claim){
          btn.classList.add("claimed");
          btn.disabled = true;
        }
      });
    }

    if(data.status === "INVALID"){
      box.classList.add("invalid");
      box.innerText = "Invalid Claim ❌";
    }

    if(data.status === "ALREADY"){
      box.classList.add("already");
      box.innerText = "Already Claimed ⚠️";
    }

    setTimeout(()=> box.className = "claim-status", 2500);
  }

  if(type === "SCORE_UPDATE"){
    const ul = document.getElementById("score-list");
    ul.innerHTML = "";
    Object.entries(data.scores || {}).forEach(([p,s])=>{
      const li = document.createElement("li");
      li.innerText = `${p}: ${s}`;
      ul.appendChild(li);
    });
  }

  if(type === "GAME_ENDED"){
    const ol = document.getElementById("leaderboard-list");
    ol.innerHTML = "";
    data.leaderboard.forEach(p=>{
      const li = document.createElement("li");
      li.innerText = `${p.name} - ${p.score}`;
      ol.appendChild(li);
    });
    showScreen("leaderboard-screen");
  }
};

/* ================= BUTTONS ================= */
document.getElementById("create-room-btn").onclick = () => {
  const name = document.getElementById("player-name").value.trim();
  const mode = document.querySelector("input[name=mode]:checked").value;
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
  document.getElementById("start-game-btn").style.display = "none";
  showScreen("waiting-screen");
};

document.getElementById("start-game-btn").onclick = () => {
  if(isHost){
    socket.send(JSON.stringify({ type: "START_GAME" }));
  }
};

document.getElementById("draw-btn").onclick = () =>
  socket.send(JSON.stringify({ type: "DRAW_NUMBER" }));

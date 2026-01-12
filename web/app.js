const WS_URL = "wss://tambola-f6di.onrender.com";
const socket = new WebSocket(WS_URL);

let isHost = false;
let marked = new Set();
let gameMode = "AUTO";

/* ===== MANUAL MODE VALIDATION VARS ===== */
let currentNumber = null;
let numberTimestamp = 0;
const MARK_WINDOW = 10000; // 10 seconds

/* ===== UI HELPERS ===== */
function showScreen(id){
  document.querySelectorAll(".screen").forEach(s =>
    s.classList.remove("active")
  );
  document.getElementById(id).classList.add("active");
}

/* ===== TICKET RENDER ===== */
function renderTicket(ticket){
  const div = document.getElementById("ticket");
  div.innerHTML = "";
  marked.clear();

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
        c.dataset.number = n;

        /* ===== MANUAL CLICK LOGIC ===== */
        c.onclick = () => {
          if(gameMode !== "MANUAL") return;

          const clickedNumber = Number(c.dataset.number);
          const now = Date.now();

          // ❌ No number drawn yet
          if(currentNumber === null){
            c.classList.remove("marked");
            marked.delete(clickedNumber);
            return;
          }

          // ❌ Time expired
          if(now - numberTimestamp > MARK_WINDOW){
            c.classList.remove("marked");
            marked.delete(clickedNumber);
            return;
          }

          // ❌ Wrong number
          if(clickedNumber !== currentNumber){
            c.classList.remove("marked");
            marked.delete(clickedNumber);
            return;
          }

          // ✅ Correct number in time
          c.classList.add("marked");
          marked.add(clickedNumber);
        };
      }

      r.appendChild(c);
    });

    div.appendChild(r);
  });
}

/* ===== CLAIM ===== */
function claim(type){
  socket.send(JSON.stringify({
    type: "MAKE_CLAIM",
    data: { claim: type }
  }));
}

function showClaim(msg, cls){
  const box = document.getElementById("claim-status");
  box.className = `claim-status show ${cls}`;
  box.innerText = msg;
  setTimeout(() => box.className = "claim-status", 2000);
}

/* ===== SOCKET EVENTS ===== */
socket.onmessage = e => {
  const { type, data } = JSON.parse(e.data);

  if(type === "CLAIM_RESULT"){
    if(data.status === "SUCCESS")
      showClaim(`${data.player} claimed ${data.claim}`, "success");
    if(data.status === "INVALID")
      showClaim("Invalid Claim", "invalid");
    if(data.status === "ALREADY")
      showClaim("Already Claimed", "already");
  }

  if(type === "ROOM_CREATED"){
    document.getElementById("room-id").innerText = data.room_id;
    isHost = true;
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
    showScreen("game-screen");
    if(isHost)
      document.getElementById("draw-btn").style.display = "block";
  }

  /* ===== NUMBER DRAWN ===== */
  if(type === "NUMBER_DRAWN"){
    document.getElementById("current-number").innerText = data.number;

    currentNumber = Number(data.number);
    numberTimestamp = Date.now();

    /* 🔒 AUTOMATIC MODE — UNCHANGED */
    if(gameMode === "AUTO"){
      document.querySelectorAll(".ticket-cell").forEach(c=>{
        if(c.dataset.number == data.number){
          c.classList.add("marked");
          marked.add(Number(c.dataset.number));
        }
      });
    }
  }

  if(type === "SCORE_UPDATE"){
    const ul = document.getElementById("score-list");
    ul.innerHTML = "";
    Object.entries(data.scores).forEach(([p,s])=>{
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

/* ===== BUTTON EVENTS ===== */
document.getElementById("create-room-btn").onclick = () => {
  const name = document.getElementById("player-name").value.trim();
  if(!name) return;

  const mode =
    document.querySelector('input[name="mode"]:checked').value;

  gameMode = mode;

  socket.send(JSON.stringify({
    type: "CREATE_ROOM",
    data: { player_name: name, mode: mode }
  }));
};

document.getElementById("join-room-btn").onclick = () => {
  const name = document.getElementById("player-name").value.trim();
  const room = document.getElementById("room-input").value.trim();
  if(!name || !room) return;

  gameMode = "AUTO"; 

  socket.send(JSON.stringify({
    type: "JOIN_ROOM",
    data: { player_name: name, room_id: room }
  }));

  showScreen("waiting-screen");
};

document.getElementById("start-game-btn").onclick = () => {
  socket.send(JSON.stringify({ type: "START_GAME" }));
};

document.getElementById("draw-btn").onclick = () => {
  socket.send(JSON.stringify({ type: "DRAW_NUMBER" }));
};

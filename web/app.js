const WS_URL="wss://tambola-f6di.onrender.com";
const socket=new WebSocket(WS_URL);

let isHost=false;
let marked=new Set();

function showScreen(id){
  document.querySelectorAll(".screen").forEach(s=>s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function renderTicket(ticket){
  const div=document.getElementById("ticket");
  div.innerHTML="";
  marked.clear();

  ticket.forEach(row=>{
    const r=document.createElement("div");
    r.className="ticket-row";
    row.forEach(n=>{
      const c=document.createElement("div");
      if(n===0){
        c.className="ticket-cell empty";
        c.innerHTML="&nbsp;";
      }else{
        c.className="ticket-cell";
        c.innerText=n;
        c.dataset.number=n;
      }
      r.appendChild(c);
    });
    div.appendChild(r);
  });
}

function claim(type){
  socket.send(JSON.stringify({type:"MAKE_CLAIM",data:{claim:type}}));
}

function showClaim(msg,cls){
  const box=document.getElementById("claim-status");
  box.className=`claim-status show ${cls}`;
  box.innerText=msg;
  setTimeout(()=>box.className="claim-status",2000);
}

socket.onmessage=e=>{
  const {type,data}=JSON.parse(e.data);

  if(type==="CLAIM_RESULT"){
    if(data.status==="SUCCESS") showClaim(`${data.player} claimed ${data.claim}`,"success");
    if(data.status==="INVALID") showClaim("Invalid Claim","invalid");
    if(data.status==="ALREADY") showClaim("Already Claimed","already");
  }

  if(type==="ROOM_CREATED"){
    document.getElementById("room-id").innerText=data.room_id;
    isHost=true;
    showScreen("waiting-screen");
  }

  if(type==="PLAYERS_UPDATE"){
    const ul=document.getElementById("players-list");
    ul.innerHTML="";
    data.players.forEach(p=>{
      const li=document.createElement("li");
      li.innerText=p;
      ul.appendChild(li);
    });
  }

  if(type==="TICKET_ASSIGNED") renderTicket(data.ticket);

  if(type==="GAME_STARTED"){
    showScreen("game-screen");
    if(isHost) document.getElementById("draw-btn").style.display="block";
  }

  if(type==="NUMBER_DRAWN"){
    document.getElementById("current-number").innerText=data.number;
    document.querySelectorAll(".ticket-cell").forEach(c=>{
      if(c.dataset.number==data.number){
        c.classList.add("marked");
        marked.add(Number(c.dataset.number));
      }
    });
  }

  if(type==="SCORE_UPDATE"){
    const ul=document.getElementById("score-list");
    ul.innerHTML="";
    Object.entries(data.scores).forEach(([p,s])=>{
      const li=document.createElement("li");
      li.innerText=`${p}: ${s}`;
      ul.appendChild(li);
    });
  }

  if(type==="GAME_ENDED"){
    const ol=document.getElementById("leaderboard-list");
    ol.innerHTML="";
    data.leaderboard.forEach(p=>{
      const li=document.createElement("li");
      li.innerText=`${p.name} - ${p.score}`;
      ol.appendChild(li);
    });
    showScreen("leaderboard-screen");
  }
};

document.getElementById("create-room-btn").onclick=()=>{
  const name=document.getElementById("player-name").value.trim();
  if(!name)return;
  socket.send(JSON.stringify({type:"CREATE_ROOM",data:{player_name:name}}));
};

document.getElementById("join-room-btn").onclick=()=>{
  const name=document.getElementById("player-name").value.trim();
  const room=document.getElementById("room-input").value.trim();
  if(!name||!room)return;
  socket.send(JSON.stringify({type:"JOIN_ROOM",data:{player_name:name,room_id:room}}));
  showScreen("waiting-screen");
};

document.getElementById("start-game-btn").onclick=()=>socket.send(JSON.stringify({type:"START_GAME"}));
document.getElementById("draw-btn").onclick=()=>socket.send(JSON.stringify({type:"DRAW_NUMBER"}));

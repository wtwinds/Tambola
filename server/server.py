import asyncio
import json
import random
import websockets
import uuid
import time
from http import HTTPStatus
from websockets.http import Headers

rooms = {}

# ------------------ HELPERS ------------------
def generate_ticket():
    nums = list(range(1, 91))
    random.shuffle(nums)
    ticket = [[0]*9 for _ in range(3)]
    for r in range(3):
        for c in random.sample(range(9), 5):
            ticket[r][c] = nums.pop()
    return ticket

def broadcast(room_id, message):
    room = rooms.get(room_id)
    if not room:
        return
    for ws in list(room["players"]):
        asyncio.create_task(ws.send(json.dumps(message)))

# ------------------ HEALTH CHECK FIX ------------------
async def process_request(path, request_headers):
    # Render / browser HEAD / GET checks
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return HTTPStatus.OK, Headers(), b"OK"
    return None

# ------------------ MAIN HANDLER ------------------
async def handler(ws):
    room_id = None
    player_name = None

    try:
        async for msg in ws:
            data = json.loads(msg)
            t = data.get("type")
            p = data.get("data", {})

            # CREATE ROOM
            if t == "CREATE_ROOM":
                player_name = p["player_name"]
                mode = p.get("mode", "AUTO")

                room_id = str(uuid.uuid4())[:6]
                rooms[room_id] = {
                    "players": {ws: player_name},
                    "tickets": {},
                    "host": ws,
                    "numbers": random.sample(range(1, 91), 90),
                    "called": [],
                    "draw_times": {},
                    "scores": {player_name: 0},
                    "claims": {},  # claim_type -> player
                    "mode": mode
                }

                await ws.send(json.dumps({
                    "type": "ROOM_CREATED",
                    "data": {"room_id": room_id}
                }))

            # JOIN ROOM
            elif t == "JOIN_ROOM":
                room_id = p["room_id"]
                player_name = p["player_name"]
                room = rooms.get(room_id)
                if not room:
                    continue

                room["players"][ws] = player_name
                room["scores"][player_name] = 0

                broadcast(room_id, {
                    "type": "PLAYERS_UPDATE",
                    "data": {"players": list(room["scores"].keys())}
                })

            # START GAME
            elif t == "START_GAME":
                room = rooms.get(room_id)
                if not room or ws != room["host"]:
                    continue

                for pws in room["players"]:
                    ticket = generate_ticket()
                    room["tickets"][pws] = ticket
                    await pws.send(json.dumps({
                        "type": "TICKET_ASSIGNED",
                        "data": {"ticket": ticket}
                    }))

                broadcast(room_id, {"type": "GAME_STARTED"})

            # DRAW NUMBER
            elif t == "DRAW_NUMBER":
                room = rooms.get(room_id)
                if not room or ws != room["host"]:
                    continue
                if not room["numbers"]:
                    continue

                num = room["numbers"].pop()
                room["called"].append(num)
                room["draw_times"][num] = time.time()

                broadcast(room_id, {
                    "type": "NUMBER_DRAWN",
                    "data": {"number": num}
                })

            # CLAIM
            elif t == "MAKE_CLAIM":
                room = rooms.get(room_id)
                if not room:
                    continue

                claim = p["claim"]

                # Already claimed by someone
                if claim in room["claims"]:
                    await ws.send(json.dumps({
                        "type": "CLAIM_RESULT",
                        "data": {"status": "ALREADY"}
                    }))
                    continue

                # Accept claim
                room["claims"][claim] = player_name
                room["scores"][player_name] += 10

                broadcast(room_id, {
                    "type": "CLAIM_RESULT",
                    "data": {
                        "status": "SUCCESS",
                        "player": player_name,
                        "claim": claim
                    }
                })

                broadcast(room_id, {
                    "type": "SCORE_UPDATE",
                    "data": {"scores": room["scores"]}
                })

    finally:
        if room_id and room_id in rooms:
            room = rooms[room_id]
            room["players"].pop(ws, None)
            room["tickets"].pop(ws, None)
            if not room["players"]:
                rooms.pop(room_id, None)

# ------------------ START SERVER ------------------
async def main():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        process_request=process_request
    ):
        print("WebSocket server running on port 8765")
        await asyncio.Future()

asyncio.run(main())

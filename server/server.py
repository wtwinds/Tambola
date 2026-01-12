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

def flatten(ticket):
    return {n for row in ticket for n in row if n != 0}

def broadcast(room_id, msg):
    room = rooms.get(room_id)
    if not room:
        return
    for ws in list(room["players"]):
        asyncio.create_task(ws.send(json.dumps(msg)))

# ------------------ HEAD / HEALTH FIX (SYNC!) ------------------
def process_request(path, headers):
    # Allow Render/Proxy HEAD & GET without WS upgrade
    if headers.get("Upgrade", "").lower() != "websocket":
        return HTTPStatus.OK, Headers(), b"OK"
    return None

# ------------------ CLAIM VALIDATION ------------------
def is_valid_claim(claim, ticket, marked):
    if claim == "QUICK_5":
        return len(marked) >= 5
    if claim == "FIRST_LINE":
        return all(n in marked for n in ticket[0] if n != 0)
    if claim == "SECOND_LINE":
        return all(n in marked for n in ticket[1] if n != 0)
    if claim == "THIRD_LINE":
        return all(n in marked for n in ticket[2] if n != 0)
    if claim == "FOUR_CORNERS":
        corners = [ticket[0][0], ticket[0][8], ticket[2][0], ticket[2][8]]
        return all(n in marked for n in cornersью
    if claim == "TAMBOLA":
        return all(n in marked for row in ticket for n in row if n != 0)
    return False

# ------------------ MAIN HANDLER ------------------
async def handler(ws):
    room_id = None
    player = None

    try:
        async for msg in ws:
            data = json.loads(msg)
            t = data["type"]
            p = data.get("data", {})

            if t == "CREATE_ROOM":
                player = p["player_name"]
                mode = p.get("mode", "AUTO")
                room_id = str(uuid.uuid4())[:6]

                rooms[room_id] = {
                    "players": {ws: player},
                    "tickets": {},
                    "marked": {},
                    "host": ws,
                    "numbers": random.sample(range(1, 91), 90),
                    "called": [],
                    "draw_times": {},
                    "scores": {player: 0},
                    "claims": {},
                    "mode": mode
                }

                await ws.send(json.dumps({
                    "type": "ROOM_CREATED",
                    "data": {"room_id": room_id}
                }))

            elif t == "JOIN_ROOM":
                room_id = p["room_id"]
                player = p["player_name"]
                room = rooms.get(room_id)
                if not room:
                    continue

                room["players"][ws] = player
                room["scores"][player] = 0

                broadcast(room_id, {
                    "type": "PLAYERS_UPDATE",
                    "data": {"players": list(room["scores"].keys())}
                })

            elif t == "START_GAME":
                room = rooms.get(room_id)
                if not room or ws != room["host"]:
                    continue

                for pws in room["players"]:
                    ticket = generate_ticket()
                    room["tickets"][pws] = ticket
                    room["marked"][pws] = set()
                    await pws.send(json.dumps({
                        "type": "TICKET_ASSIGNED",
                        "data": {"ticket": ticket}
                    }))

                broadcast(room_id, {
                    "type": "GAME_STARTED",
                    "data": {"mode": room["mode"]}
                })

            elif t == "DRAW_NUMBER":
                room = rooms.get(room_id)
                if not room or ws != room["host"] or not room["numbers"]:
                    continue

                num = room["numbers"].pop()
                room["called"].append(num)
                room["draw_times"][num] = time.time()

                if room["mode"] == "AUTO":
                    for pws, ticket in room["tickets"].items():
                        if num in flatten(ticket):
                            room["marked"][pws].add(num)

                broadcast(room_id, {
                    "type": "NUMBER_DRAWN",
                    "data": {"number": num}
                })

            elif t == "MARK_NUMBER":
                room = rooms.get(room_id)
                if room["mode"] != "MANUAL":
                    continue
                num = p["number"]
                draw_time = room["draw_times"].get(num)
                if not draw_time or time.time() - draw_time > 10:
                    continue
                ticket = room["tickets"].get(ws)
                if ticket and num in flatten(ticket):
                    room["marked"][ws].add(num)

            elif t == "MAKE_CLAIM":
                room = rooms.get(room_id)
                claim = p["claim"]

                if claim in room["claims"]:
                    await ws.send(json.dumps({
                        "type": "CLAIM_RESULT",
                        "data": {"status": "ALREADY"}
                    }))
                    continue

                ticket = room["tickets"][ws]
                marked = room["marked"][ws]

                if not is_valid_claim(claim, ticket, marked):
                    await ws.send(json.dumps({
                        "type": "CLAIM_RESULT",
                        "data": {"status": "INVALID"}
                    }))
                    continue

                room["claims"][claim] = player
                room["scores"][player] += 10

                broadcast(room_id, {
                    "type": "CLAIM_RESULT",
                    "data": {
                        "status": "SUCCESS",
                        "player": player,
                        "claim": claim
                    }
                })
                broadcast(room_id, {
                    "type": "SCORE_UPDATE",
                    "data": {"scores": room["scores"]}
                })

    finally:
        if room_id and room_id in rooms:
            rooms[room_id]["players"].pop(ws, None)
            rooms[room_id]["marked"].pop(ws, None)
            if not rooms[room_id]["players"]:
                rooms.pop(room_id, None)

# ------------------ START SERVER (FIXED PORT) ------------------
async def main():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        process_request=process_request
    ):
        print("WebSocket running on port 8765")
        await asyncio.Future()

asyncio.run(main())

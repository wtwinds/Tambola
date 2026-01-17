import asyncio, json, os, random, string, websockets

PORT = int(os.environ.get("PORT", 10000))
rooms = {}

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# ---------- TICKET ----------
def generate_ticket():
    ticket = [[0]*9 for _ in range(3)]
    row_cols = [sorted(random.sample(range(9), 5)) for _ in range(3)]

    for r in range(3):
        for c in row_cols[r]:
            ticket[r][c] = -1

    for c in range(9):
        rows = [r for r in range(3) if ticket[r][c] == -1]
        if not rows:
            continue
        start = c * 10 + 1
        end = 90 if c == 8 else start + 9
        nums = sorted(random.sample(range(start, end + 1), len(rows)))
        for r, n in zip(rows, nums):
            ticket[r][c] = n

    return ticket

def flatten(ticket):
    return [n for row in ticket for n in row if n != 0]

async def broadcast(room, msg):
    for ws in room["sockets"]:
        await ws.send(json.dumps(msg))

# ---------- CLAIM CHECK ----------
def validate_claim(claim, ticket, drawn):
    rows = [[n for n in row if n != 0] for row in ticket]
    all_nums = flatten(ticket)

    if claim == "QUICK_5":
        return len([n for n in all_nums if n in drawn]) >= 5

    if claim == "FIRST_LINE":
        return all(n in drawn for n in rows[0])

    if claim == "SECOND_LINE":
        return all(n in drawn for n in rows[1])

    if claim == "THIRD_LINE":
        return all(n in drawn for n in rows[2])

    if claim == "FOUR_CORNERS":
        corners = [ticket[0][0], ticket[0][8], ticket[2][0], ticket[2][8]]
        corners = [n for n in corners if n != 0]
        return all(n in drawn for n in corners)

    if claim == "TAMBOLA":
        return all(n in drawn for n in all_nums)

    return False

# ---------- MAIN ----------
async def handler(ws):
    room_id = None
    player = None

    async for msg in ws:
        data = json.loads(msg)
        t = data["type"]
        d = data.get("data", {})

        if t == "CREATE_ROOM":
            player = d["player_name"]
            room_id = generate_room_id()

            rooms[room_id] = {
                "host": ws,
                "players": [player],
                "sockets": [ws],
                "tickets": {},
                "numbers": set(),
                "scores": {},
                "claims_won": {},      # ✅ ADD
                "claimed": set(),
                "started": False,
                "ended": False,
                "mode": d.get("mode", "AUTO")
            }

            await ws.send(json.dumps({
                "type": "ROOM_CREATED",
                "data": {"room_id": room_id}
            }))

            await broadcast(rooms[room_id], {
                "type": "PLAYERS_UPDATE",
                "data": {"players": rooms[room_id]["players"]}
            })

        elif t == "JOIN_ROOM":
            room_id = d["room_id"]
            player = d["player_name"]
            room = rooms.get(room_id)
            if not room:
                continue

            room["players"].append(player)
            room["sockets"].append(ws)

            await broadcast(room, {
                "type": "PLAYERS_UPDATE",
                "data": {"players": room["players"]}
            })

        elif t == "START_GAME":
            room = rooms.get(room_id)
            if not room or ws != room["host"]:
                continue

            room["started"] = True

            for i, p in enumerate(room["players"]):
                room["tickets"][p] = generate_ticket()
                room["scores"][p] = 0
                room["claims_won"][p] = []   # ✅ INIT
                await room["sockets"][i].send(json.dumps({
                    "type": "TICKET_ASSIGNED",
                    "data": {"ticket": room["tickets"][p]}
                }))

            await broadcast(room, {
                "type": "GAME_STARTED",
                "data": {"mode": room["mode"]}
            })

        elif t == "DRAW_NUMBER":
            room = rooms.get(room_id)
            if not room or not room["started"] or room["ended"]:
                continue

            n = random.randint(1, 90)
            while n in room["numbers"]:
                n = random.randint(1, 90)

            room["numbers"].add(n)

            await broadcast(room, {
                "type": "NUMBER_DRAWN",
                "data": {"number": n}
            })

        elif t == "MAKE_CLAIM":
            room = rooms.get(room_id)
            if not room or not room["started"]:
                continue

            claim = d["claim"]
            ticket = room["tickets"].get(player)

            if claim in room["claimed"]:
                await ws.send(json.dumps({
                    "type": "CLAIM_RESULT",
                    "data": {"status": "ALREADY", "claim": claim}
                }))
                continue

            if not ticket or not validate_claim(claim, ticket, room["numbers"]):
                await ws.send(json.dumps({
                    "type": "CLAIM_RESULT",
                    "data": {"status": "INVALID", "claim": claim}
                }))
                continue

            room["claimed"].add(claim)
            room["scores"][player] += 1
            room["claims_won"][player].append(claim)   # ✅ ADD

            await broadcast(room, {
                "type": "CLAIM_RESULT",
                "data": {"status": "SUCCESS", "claim": claim, "player": player}
            })

            await broadcast(room, {
                "type": "SCORE_UPDATE",
                "data": {
                    "scores": room["scores"],
                    "claims_won": room["claims_won"]   # ✅ ADD
                }
            })

            if claim == "TAMBOLA":
                room["ended"] = True
                leaderboard = sorted(room["scores"].items(),
                                     key=lambda x: x[1],
                                     reverse=True)

                await broadcast(room, {
                    "type": "GAME_ENDED",
                    "data": {
                        "leaderboard": [
                            {"name": p, "score": s} for p, s in leaderboard
                        ]
                    }
                })

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print("Server running on", PORT)
        await asyncio.Future()

asyncio.run(main())

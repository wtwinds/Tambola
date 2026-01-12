import asyncio, json, random, uuid, time, os
import websockets
from http import HTTPStatus
from websockets.http import Headers

rooms = {}

def generate_ticket():
    nums=list(range(1,91))
    random.shuffle(nums)
    ticket=[[0]*9 for _ in range(3)]
    for r in range(3):
        for c in random.sample(range(9),5):
            ticket[r][c]=nums.pop()
    return ticket

def broadcast(room_id,msg):
    for ws in list(rooms[room_id]["players"]):
        asyncio.create_task(ws.send(json.dumps(msg)))

def process_request(path,headers):
    if headers.get("Upgrade","").lower()!="websocket":
        return HTTPStatus.OK,Headers(),b"OK"
    return None

async def handler(ws):
    room_id=None
    player=None

    try:
        async for msg in ws:
            data=json.loads(msg)
            t=data["type"]
            p=data.get("data",{})

            if t=="CREATE_ROOM":
                player=p["player_name"]
                mode=p.get("mode","AUTO")
                room_id=str(uuid.uuid4())[:6]

                rooms[room_id]={
                    "players":{ws:player},
                    "tickets":{},
                    "host":ws,
                    "numbers":random.sample(range(1,91),90),
                    "called":[],
                    "draw_times":{},
                    "scores":{player:0},
                    "claims":{},
                    "mode":mode
                }
                await ws.send(json.dumps({"type":"ROOM_CREATED","data":{"room_id":room_id}}))

            elif t=="JOIN_ROOM":
                room_id=p["room_id"]
                player=p["player_name"]
                r=rooms.get(room_id)
                if not r: continue
                r["players"][ws]=player
                r["scores"][player]=0
                broadcast(room_id,{"type":"PLAYERS_UPDATE","data":{"players":list(r["scores"].keys())}})

            elif t=="START_GAME":
                r=rooms[room_id]
                if ws!=r["host"]: continue
                for pws in r["players"]:
                    ticket=generate_ticket()
                    r["tickets"][pws]=ticket
                    await pws.send(json.dumps({"type":"TICKET_ASSIGNED","data":{"ticket":ticket}}))
                broadcast(room_id,{"type":"GAME_STARTED"})

            elif t=="DRAW_NUMBER":
                r=rooms[room_id]
                if ws!=r["host"] or not r["numbers"]: continue
                num=r["numbers"].pop()
                r["called"].append(num)
                r["draw_times"][num]=time.time()
                broadcast(room_id,{"type":"NUMBER_DRAWN","data":{"number":num}})

            elif t=="MAKE_CLAIM":
                r=rooms[room_id]
                claim=p["claim"]

                if claim in r["claims"]:
                    await ws.send(json.dumps({"type":"CLAIM_RESULT","data":{"status":"ALREADY"}}))
                    continue

                r["claims"][claim]=player
                r["scores"][player]+=10

                broadcast(room_id,{
                    "type":"CLAIM_RESULT",
                    "data":{"status":"SUCCESS","player":player,"claim":claim}
                })
                broadcast(room_id,{"type":"SCORE_UPDATE","data":{"scores":r["scores"]}})

    finally:
        if room_id and room_id in rooms:
            rooms[room_id]["players"].pop(ws,None)
            if not rooms[room_id]["players"]:
                rooms.pop(room_id)

async def main():
    port=int(os.environ.get("PORT",10000))
    async with websockets.serve(handler,"0.0.0.0",port,process_request=process_request):
        print("WS running on",port)
        await asyncio.Future()

asyncio.run(main())

import httpx
from gokgs.app import app
from gokgs.redis import r
import json

url_games = 'http://localhost:8081/ROOM_LOAD_GAME'

@app.get('/game/{game_timestamp}')
async def get_game(game_timestamp: str):
    action = f'GAME_PAST_INFORMATION_{game_timestamp}'
    client = httpx.AsyncClient()
    body = {
        'private': True,
        'timestamp': game_timestamp,
        'channelId': 5
    }
    redis = r()
    await redis.lpush('TIMESTAMP_QUERY', game_timestamp)
    try:
        await client.post(url_games, json=body)
        while not (keys := await redis.keys(action)):
            pass
    finally:
        await client.aclose()
    result = json.loads(await redis.get(keys[0]))['sgfEvents']
    res = {
        "gameSummary": result[0]['props'],
        "sgfEvents": list(filter(lambda ob:ob['type']=='PROP_GROUP_ADDED',result[1:]))
    }
    return res

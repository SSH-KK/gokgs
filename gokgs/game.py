import httpx
from gokgs.app import app
from gokgs.redis import r
import json

url_games = 'http://localhost:8081/ROOM_LOAD_GAME'
game_summary_keys = ['gameType','komi','size','white','black']

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
    result = json.loads(await redis.get(keys[0]))
    result['gameSummary'] = {**result['gameSummary'],**result['gameSummary']['players']}
    res = {
        "gameSummary": {key:result['gameSummary'][key] for key in game_summary_keys},
        "events": [{**ob['props'][0]['loc'],'color':ob['props'][0]['color']} if type(ob['props'][0]['loc'])==dict else {} for ob in list(filter(lambda ob:ob['type']=='PROP_GROUP_ADDED',result['sgfEvents'][1:]))]
    }
    return res

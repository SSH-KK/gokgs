import json

import httpx

from gokgs.app import app
from gokgs.redis import r

url_games = 'http://localhost:8081/ROOM_LOAD_GAME'
game_summary_keys = ['gameType', 'komi', 'size', 'white', 'black']

@app.get('/game/{game_timestamp}')
async def get_game(game_timestamp: str):
    redis = r()
    await redis.lpush('TIMESTAMP_QUERY', game_timestamp)
    async with httpx.AsyncClient() as client:
        body = {  # post request to url_games
            'private': True,
            'timestamp': game_timestamp,
            'channelId': 5
        }
        await client.post(url_games, json=body)
    action = f'GAME_PAST_INFORMATION_{game_timestamp}'
    while not (keys := await redis.keys(action)):
        pass
    answer = json.loads(await redis.get(keys[0]))
    answer, events = answer['gameSummary'], answer['sgfEvents'][1:]
    answer |= answer['players']
    res = {
        'gameSummary': {
            key: answer[key]
            for key in game_summary_keys
        },
        'events': [
            {
                **e['props'][0]['loc'],
                'color': e['props'][0]['color']
            } if isinstance(e['props'][0]['loc'], dict) else {}
            for e in events[1:]
            if e['type'] == 'PROP_GROUP_ADDED'
        ]
    }
    return res

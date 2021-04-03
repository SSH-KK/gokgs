import json

import httpx

from gokgs.app import app
from gokgs.redis import r

url_games = 'http://localhost:8081/ROOM_LOAD_GAME'
game_summary_keys = ['gameType', 'komi', 'size', 'white', 'black']

associated_keys = {
    'MOVE': 'events',
    'TERRITORY': 'points'
}

@app.get('/game/{game_timestamp}')
async def get_game(game_timestamp: str):
    redis = r()
    action = f'GAME_PAST_INFORMATION_{game_timestamp}'
    client = httpx.AsyncClient()
    body = {
        'private': True,
        'timestamp': game_timestamp,
        'channelId': 5
    }
    await redis.lpush('TIMESTAMP_QUERY', game_timestamp)
    async with httpx.AsyncClient() as client:
        body = {  # post request to url_games
            'private': True,
            'timestamp': game_timestamp,
            'channelId': 5
        }
        await client.post(url_games, json=body)
        while not (keys := await redis.keys(action)):
            pass
    result = json.loads(await redis.get(keys[0]))
    gameSummary, all_events = result['gameSummary'], [ob for ob in result['sgfEvents'][1:] if ob['type'] == 'PROP_GROUP_ADDED']
    gameSummary |= gameSummary['players']
    sgfEvents = {'events': [], 'points': []}
    for ob in all_events:
        for prop in ob['props']:
            if prop['name'] in associated_keys.keys():
                sgfEvents[associated_keys[prop['name']]].append({
                    'position': list(prop['loc'].values()) if isinstance(prop['loc'], dict) else prop['loc'],
                    'color':prop['color']
                })
    res = {
        "gameSummary": {key: gameSummary.get(key, {}) for key in game_summary_keys},
        **sgfEvents
    }
    return res

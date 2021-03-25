import httpx
from bs4 import BeautifulSoup
from gokgs.app import app
from gokgs.redis import r
import json

url = 'https://gokgs.com/top100.jsp'
url_top = 'http://localhost:8081/JOIN_ARCHIVE_REQUEST'

@app.get('/get_top')
async def get_top_users():
    redis = r()
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15)
        if resp.status_code != 200:
            return {'result': 'error'}
    bs = BeautifulSoup(resp.text, 'lxml')
    names = bs.find_all('a')[:-1]
    places = [int(name.parent.previous_sibling.text) for name in names]
    ranks = [name.parent.next_sibling.text for name in names]
    names = [name.text for name in names]
    ans = []
    for name, rank, place in zip(names, ranks, places):
        action = f'LAST_GAMES_USER_{name}'
        print(f'user = {name}')
        keys = await redis.keys(action)
        while(not keys):
            async with httpx.AsyncClient() as client:
                await client.post(url_top, data = json.dumps({"name":name}))
                keys = await redis.keys(action)
                print('RE TRY')
        result = await redis.get(keys[0])
        res_t = []
        result = json.loads(result)['games'][::-1]
        for game in result:
            test_int = False
            if('score' in game.keys()):
                try:
                    int(game['score'])
                    test_int = True
                except:
                    test_int = False
            if('inPlay' not in game.keys() and test_int):
                res_t.append(game)
                if(len(res_t) == 2):
                    break
        ans.append({'name': name, 'rank': rank, 'place': place, 'last':res_t})
    return ans

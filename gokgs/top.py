import httpx
from bs4 import BeautifulSoup

from gokgs.app import app

url = 'https://gokgs.com/top100.jsp'


@app.get('/top')
async def top():
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {'result': 'error'}
    bs = BeautifulSoup(resp.text, 'lxml')
    names = bs.find_all('a')[:-1]
    places = [int(name.parent.previous_sibling.text) for name in names]
    ranks = [name.parent.next_sibling.text for name in names]
    names = [name.text for name in names]
    return [
        {'name': name, 'rank': rank, 'place': place}
        for name, rank, place in zip(names, ranks, places) 
    ]

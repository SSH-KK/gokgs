import copy
import os

import httpx
from retrying_async import retry

from gokgs.app import app

URL = 'https://www.gokgs.com/json/access'
client = httpx.AsyncClient()


@retry(attempts=3, delay=3)
async def post(action, body):
    body = copy.deepcopy(body)
    body['type'] = action.upper()
    r = await client.post(URL, json=body)
    r.raise_for_status()
    return r.text


async def login(name, password):
    await post('login', {
        'name': name,
        'password': password,
        'locale': 'en_US'
    })


@app.on_event('shutdown')
async def shutdown():
    await client.aclose()


@app.on_event('startup')
async def init():
    name = os.getenv('NAME')
    password = os.getenv('PASSWORD')
    if not name or not password:
        return
    await login(name, password)

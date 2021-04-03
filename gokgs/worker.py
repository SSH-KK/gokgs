import asyncio
import copy
import os
import sys
import time
import json

import httpx
from fastapi import Request, HTTPException
from retrying_async import retry

from gokgs.app import app
from gokgs.redis import r

URL = 'https://www.gokgs.com/json/access'
_name = _password = _task = None
client = httpx.AsyncClient()
logged_in = False


@retry(attempts=3, delay=1)
async def post(action, body):
    body = copy.deepcopy(body)
    body['type'] = action.upper()
    body = json.dumps(body)
    resp = await client.post(URL, data=body)
    resp.raise_for_status()
    return resp.text


async def login(name, password):
    await post('login', {
        'name': name,
        'password': password,
        'locale': 'en_US'
    })


async def get():
    global logged_in
    resp = await client.get(URL, timeout=20)
    resp.raise_for_status()
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = {}
    msgs = body.get('messages', [])
    if len(msgs) and msgs[-1]['type'] == 'LOGOUT':
        logged_in = False
    elif any(msg['type'] == 'LOGIN_SUCCESS' for msg in msgs):
        logged_in = True
    return msgs



async def loop_worker():
    redis = r()
    try:
        while True:
            try:
                msgs = await get()
                timestamp = time.time_ns()
                for i, msg in enumerate(msgs):
                    t = msg.get('type', 'UNKNOWN_TYPE')
                    #print(f'new_key = {t}')
                    if t == 'LOGIN_SUCCESS':
                        await post('JOIN_REQUEST', {"channelId": 5})
                    if t == 'ARCHIVE_JOIN':
                        username = msg.get('user', {}).get('name', 'UNKNOWN_USER')
                        key = f'LAST_GAMES_USER_{username}'
                    elif t == 'GAME_JOIN':
                        query = await redis.lpop('TIMESTAMP_QUERY')  # oops... may broke here
                        key = f'GAME_PAST_INFORMATION_{query}'
                    else:
                        key = f'{t}_{timestamp}_{i}'
                    await redis.set(key, json.dumps(msg), expire=3600)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(e)
                await login(_name, _password)
    except asyncio.CancelledError:
        pass


@app.get('/is_logged')
async def is_logged():
    return {'loggedIn': logged_in}


@app.post('/login')
async def login_route(username: str, password: str):  # yew, its bad but fast
    global _name, _password, _task
    _name = username
    _password = password
    await login(username, password)
    if _task:
        _task.cancel()
    _task = asyncio.create_task(loop_worker())
    return 'check get /LOGIN'


@app.post('/{action}')
async def post_route(action: str, req: Request):
    body = await req.json()
    try:
        resp = await post(action, body)
        return {'result': 'ok'}
    except Exception as e:
        return {
            'result': 'error',
            'detail': str(e)
        }


@app.get('/{action}')
async def get_route(action: str, order: str = 'all', delete: bool = True):
    if order not in ('all', 'first', 'last'):
        raise HTTPException(status_code=400, detail='invalid order')
    redis = r()
    action = action.upper() + '_*'
    keys = await redis.keys(action)
    if not keys:
        return {}
    keys.sort()
    if order == 'first':
        keys = keys[:1]
    elif order == 'last':
        keys = keys[-1:]
    result = await redis.mget(*keys)
    result = {k: v for k, v in zip(keys, result)}
    if delete:
        await redis.delete(*keys)
    return result


@app.on_event('shutdown')
async def shutdown():
    if _task:
        _task.cancel()
    await client.aclose()


@app.on_event('startup')
async def init():
    global _name, _password, _task
    _name = os.getenv('NAME')
    _password = os.getenv('PASSWORD')
    if not _name or not _password:
        return
    await login(_name, _password)
    _task = asyncio.create_task(loop_worker())


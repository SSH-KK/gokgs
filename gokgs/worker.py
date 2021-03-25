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


@retry(attempts=3, delay=1)
async def post(action, body):
    body = copy.deepcopy(body)
    body['type'] = action.upper()
    resp = await client.post(URL, json=body)
    resp.raise_for_status()
    return resp.text


async def login(name, password):
    await post('login', {
        'name': name,
        'password': password,
        'locale': 'en_US'
    })


async def get():
    resp = await client.get(URL, timeout=15)
    resp.raise_for_status()
    try:
        return resp.json()
    except json.JSONDecodeError:
        return {}


async def loop_worker():
    redis = r()
    try:
        while True:
            try:
                resp = await get()
                msgs = resp.get('messages', [])
                timestamp = time.time_ns()
                for i, msg in enumerate(msgs):
                    t = msg.get('type', 'UNKNOWN_TYPE')
                    if t == 'ARCHIVE_JOIN':
                        username = msg.get('user', {}).get('name', 'UNKNOWN_USER')
                        key = f'LAST_GAMES_USER_{username}'
                    else:
                        key = f'{t}_{timestamp}_{i}'
                    await redis.set(key, json.dumps(msg), expire=3600)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(e, file=sys.stderr)
                await login(_name, _password)
    except asyncio.CancelledError:
        pass


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
    #print(f'keys = {keys}')
    if not keys:
        return {}
    keys.sort()
    if order == 'first':
        keys = keys[:1]
    elif order == 'last':
        keys = keys[-1:]
    result = await redis.mget(*keys)
    #print(f'res = {result}')
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

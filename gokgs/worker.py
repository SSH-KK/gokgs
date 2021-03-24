import asyncio
import copy
import os
import sys
import time
import json

import httpx
from fastapi import Request
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
    resp = await client.get(URL)
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
                for msg in msgs:
                    t = msg.get('type', 'UNKNOWN_TYPE')
                    key = f'{t}_{time.time()}'
                    await redis.set(key, json.dumps(msg), expire=3600)
            except asyncio.CancelledError:
                raise
            except httpx.ReadTimeout:
                pass
            except Exception as e:
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

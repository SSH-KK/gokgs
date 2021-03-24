import os

import aioredis
from fastapi import Body

from gokgs.app import app

_redis = None


def r():
    if not _redis:
        raise ValueError('Call gokgs.redis.init first')
    return _redis


@app.on_event('startup')
async def init():
    global _redis
    _redis = await aioredis.create_redis_pool(
        os.getenv('REDIS_URI', 'redis://localhost'),
        encoding='utf8'
    )


@app.on_event('shutdown')
async def shutdown():
    if not _redis:
        return
    _redis.close()
    await _redis.wait_closed()


@app.get('/_redis')
async def get_key(key: str):
    val = await r().get(key)
    return {'key': key, 'value': val}


@app.put('/_redis')
async def get_key(key: str, value: str = Body(..., embed=True)):
    await r().set(key, value)
    return {'key': key, 'value': value}


@app.delete('/_redis')
async def get_key(key: str):
    await r().delete(key)
    return {'key': key}

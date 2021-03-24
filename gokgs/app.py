from fastapi import FastAPI

app = FastAPI(
    title='gokgs',
    version='1.0.0',
    description=''
)


@app.get('/')
def index():
    return {'it': 'works'}

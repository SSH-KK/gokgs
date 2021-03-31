import os

import uvicorn
import dotenv

from gokgs.app import app
import gokgs.redis
import gokgs.top
import gokgs.game
from gokgs import worker

dotenv.load_dotenv()

def main():
    uvicorn.run(
        'gokgs.__main__:app',
        port=8081,
        host='0.0.0.0',
        reload=os.getenv('DEBUG', '0') == '1'
    )


if __name__ == '__main__':
    main()

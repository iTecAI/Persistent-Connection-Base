from fastapi import FastAPI, Response, status
from fastapi_utils.tasks import repeat_every
import time, json
import uvicorn

from _models import *

class App:
    def __init__(
        self,
        user_management=True,
        session_timeout=30,
        user_cache='users.json'
        ):
        self.app = FastAPI()
        self.connections = {}
        self.users = {}

        # Config options
        self.user_management = user_management
        self.session_timeout = session_timeout
        self.user_cache = user_cache

        # Request events
        # Connection requests
        @self.app.post('/connections/new/')
        async def new_connection(fingerprint: str):
            if fingerprint in self.connections.keys():
                self.connections[fingerprint]['last_update'] = time.time()
            else:
                self.connections[fingerprint] = self.create_connection(fingerprint)
        @self.app.get('/connections/self/')
        async def get_connection(fingerprint: str, response: Response):
            for u in self.users.values():
                if u['owner'] == fingerprint:
                    self.connections[fingerprint] = create_connection(fingerprint)
                    break
            if not fingerprint in self.connections.keys():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    'connection':None,
                    'user':None
                }
            self.connections[fingerprint]['last_update'] = time.time()
            if self.connections[fingerprint]['current_user']:
                usr = self.users[self.connections[fingerprint]['current_user']]
            else:
                usr = None
            conn = self.connections[fingerprint].copy()
            self.connections[fingerprint]['update'] = False
            return {
                'connection':conn,
                'user':usr
            }
        
        # Interval events
        @self.app.on_event('startup')
        @repeat_every(seconds=120)
        async def check_inactive_connections():
            nc = {}
            for conn in self.connections.values():
                if conn['last_update']+self.session_timeout >= time.time():
                    nc[conn['fingerprint']] = conn.copy()
            self.connections = nc.copy()


    
    def run(self,host='localhost',port=5000,log_level='info'):
        uvicorn.run(self.app,host=host,port=port,log_level=log_level)
    
    def create_connection(self,fingerprint):
        return {
            'fingerprint':fingerprint,
            'last_update':time.time(),
            'current_user':None,
            'creation':time.time(),
            'update':True
        }
    
    # User caching ops
    def cache(self,user):
        with open(self.user_cache,'r') as f:
            old_cache = json.load(f)
        old_cache[user] = self.users[user]
        with open(self.user_cache,'w') as f:
            json.dump(old_cache,f)
    def get_cached(self,user):
        with open(self.user_cache,'r') as f:
            old_cache = json.load(f)
        return old_cache[user]
    def del_cached(self,user):
        with open(self.user_cache,'r') as f:
            old_cache = json.load(f)
        del old_cache[user]
        with open(self.user_cache,'w') as f:
            json.dump(old_cache,f)
    def load_cache(self):
        with open(self.user_cache,'r') as f:
            return json.load(f)
    

app = App()
app.run()
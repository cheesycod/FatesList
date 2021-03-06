import asyncpg
from fastapi import FastAPI, Request, Form as FForm
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette.middleware.sessions import SessionMiddleware
from config import *
from pydantic import BaseModel
import asyncio
from starlette_wtf import CSRFProtectMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
import orjson
import os
import aioredis
import discord
import importlib
import builtins
import time

intent_main = discord.Intents.default()
intent_main.typing = False
intent_main.bans = False
intent_main.emojis = False
intent_main.integrations = False
intent_main.webhooks = False
intent_main.invites = False
intent_main.voice_states = False
intent_main.messages = False
intent_main.members = True
intent_main.presences = True
builtins.client = discord.Client(intents=intent_main)


# FLimiter rl func
async def rl_key_func(request: Request) -> str:
    if request.headers.get("NGBB-RateLimitBypass") == ratelimit_bypass_key:
        return get_token(32)
    else:
        return ip_check(request)

def ip_check(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host

limiter = FastAPILimiter
app = FastAPI(default_response_class = ORJSONResponse)
app.add_middleware(SessionMiddleware, secret_key=session_key)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)
app.add_middleware(ProxyHeadersMiddleware)

@app.middleware('http')
async def add_cors_pt_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["Access-Control-Allow-Origin"] = '*'
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Bypass-Tunnel-Reminder, API-Token, User-API-Token"
    return response


print("NG BOTBLOCK: Loading Modules")
# Include all the modules
for f in os.listdir("ula/api/modules/app"):
    if not f.startswith("_"):
        print("APP MODLOAD: modules.app." + f.replace(".py", ""))
        route = importlib.import_module("ula.api.modules.app." + f.replace(".py", ""))
        app.include_router(route.router)

async def setup_db():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    # some table creation here meow
    return db

@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    asyncio.create_task(client.start(TOKEN_ULA))
    builtins.redis_db = await aioredis.from_url('redis://localhost')
    limiter.init(redis_db, identifier = rl_key_func)

@app.on_event("shutdown")
async def close():
    print("Closing")
    await redis_db.close()
    await redis_db.wait_closed()

@client.event
async def on_ready():
    print(client.user, "up")


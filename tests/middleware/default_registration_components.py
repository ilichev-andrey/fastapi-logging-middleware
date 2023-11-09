from fastapi import FastAPI, APIRouter
from starlette.responses import Response

from tests.components import ResponseGetter

response_getter = ResponseGetter()

app = FastAPI()


@app.post('/', response_class=Response)
async def root_post():
    return response_getter.get()


router_v1 = APIRouter(prefix='/v1')


@router_v1.get('/', response_class=Response)
async def v1_get():
    return response_getter.get()


@router_v1.post('/', response_class=Response)
async def v1_post():
    return response_getter.get()


@router_v1.put('/', response_class=Response)
async def v1_put():
    return response_getter.get()


@router_v1.patch('/', response_class=Response)
async def v1_patch():
    return response_getter.get()


@router_v1.delete('/', response_class=Response)
async def v1_delete():
    return response_getter.get()


@router_v1.head('/', response_class=Response)
async def v1_put():
    return response_getter.get()


app.include_router(router_v1)

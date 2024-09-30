from fastapi import FastAPI
from api import stocks, options, futures, indices, forex
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi.requests import Request
from fastapi.responses import Response


# List of allowed origins (the domains you want to allow to make requests to your API)
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Local frontend application
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,  # Allow access from these domains
        allow_credentials=True,  # Allow cookies
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )
]


app = FastAPI(middleware=middleware)


def check_routes(request: Request):
    # Using FastAPI instance
    url_list = [
        route.path for route in request.app.routes if "rest_of_path" not in route.path
    ]
    if request.url.path not in url_list:
        return Response(status_code=404)


# Handle CORS preflight requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str) -> Response:
    response = check_routes(request)
    if response:
        return response

    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS or not origin:
        response = Response(
            content="OK",
            media_type="text/plain",
            headers={
                "Access-Control-Allow-Origin": origin if origin else "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
        return response

    return Response(status_code=403, content=origin)


# Include public and private routers
app.include_router(stocks.router, prefix="/stocks")
app.include_router(futures.router, prefix="/futures")
app.include_router(indices.router, prefix="/indices")
app.include_router(options.router, prefix="/options")
app.include_router(forex.router, prefix="/forex")

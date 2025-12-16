from aiohttp import web
from web.route import routes

# client_max_size added to prevent 413 Payload Too Large errors
web_app = web.Application(client_max_size=30000000)
web_app.add_routes(routes)

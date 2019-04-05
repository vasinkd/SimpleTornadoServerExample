from models.server import WebServer, ApiAppClass
from shared import api_key, port

api_app = ApiAppClass(api_key)
web_server = WebServer(port=port, app=api_app)
web_server.start()

web_server.process.join()

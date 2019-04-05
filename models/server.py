import logging
from threading import Lock
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.web
import tornado.iostream
from tornado.log import gen_log
from tornado.web import MissingArgumentError
from multiprocessing import Process

from models import database_reader, DBReaderException  # some inside logic here
# In this example we provide info about tickets availability

logging.getLogger(__name__).addHandler(logging.NullHandler())
gen_log.disabled = True


class WebServer(object):

    def __init__(self, port, app):
        self.http_server = HTTPServer(app)  # http server, not https;
        # To move to https add ssl_options argument
        self.port = port
        self.loop = None
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.server_lock = Lock()
        self.shutdown_lock = Lock()
        self.process = Process(target=self.serve_forever, args=(),
                               name="WebServer",
                               daemon=True)

    def start(self):
        self.process.start()

    def serve_forever(self):
        with self.server_lock:
            self.is_running = True
            self.logger.debug('Webserver started')
            self.http_server.listen(self.port)
            self.loop = IOLoop.current()
            self.loop.start()
            self.logger.debug('Webserver stopped')
            self.is_running = False

    def shutdown(self):
        with self.shutdown_lock:
            if not self.is_running:
                self.logger.warning('Webserver is already stopped')
                return
            else:
                self.loop.add_callback(self.loop.stop)

    def handle_error(self, request, client_address):
        """Handle an error gracefully."""
        self.logger.debug('Exception happened during processing'
                          ' of request from %s',
                          client_address, exc_info=True)


class ApiAppClass(tornado.web.Application):

    def __init__(self, api_key):
        # Any objects you want to pass to handler, it is optional
        self.shared_objects = {"api_key": api_key}

        # (Path, Handler_it_triggers)
        handlers = [
            (r"/?", ApiHandler, self.shared_objects)
            ]
        tornado.web.Application.__init__(self, handlers)

    def log_request(self, handler):
        pass


class ApiHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["GET"]  # Type of requests permitted

    def __init__(self, application, request, **kwargs):
        super(ApiHandler, self).__init__(application, request, **kwargs)
        self.logger = logging.getLogger(__name__)

    def initialize(self, api_key):
        # if you pass shared_objects - define initialize method
        self.api_key = api_key

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def get(self):
        self.logger.debug('API triggered')
        self._validate_get()  # here is an example of using of api key
        # It will raise 403 if the key is wrong

        # Check that all required arguments are there (optional)
        try:
            city_from = self.get_argument('from')
            city_to = self.get_argument('to')
            date_str = self.get_argument('date')
        except MissingArgumentError:
            self.set_status(400)
            return self.finish("You should specify all fields:"
                               " from, to, date")

        # Inner logic
        try:
            answer = database_reader.read(city_from, date_str, city_to)
        except DBReaderException as e:
            self.set_status(400)
            answer = str(e)

        # Returning results
        self.write({"result": answer,
                    "params": {"from": city_from,
                               "to": city_to,
                               "date_str": date_str}})

    def _validate_get(self):
        # ct_header = self.request.headers.get('Content-Type', None)
        # auth_header = self.request.headers.get('Authorization', None)
        # if (ct_header != 'application/json') or (auth_header != self.api_key)
        #     raise tornado.web.HTTPError(403)
        key = self.get_argument('key', None)
        if key != self.api_key:
            raise tornado.web.HTTPError(403)

    def write_error(self, status_code, **kwargs):
        """Log an arbitrary message.

        This is used by all other logging functions.

        It overrides ``BaseHTTPRequestHandler.log_message``,
        which logs to ``sys.stderr``.

        The first argument, FORMAT, is a format string for the message to be
        logged.  If the format string contains any % escapes requiring
        parameters, they should be specified as subsequent
        arguments (it's just like printf!).

        The client ip is prefixed to every message.

        """
        super(ApiHandler, self).write_error(status_code, **kwargs)
        self.logger.debug("%s - %s" % (self.request.remote_ip,
                                       "Exception in Webserver"),
                          exc_info=kwargs['exc_info'])

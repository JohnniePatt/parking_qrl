"""HTTP transport only. All state changes are delegated to main.Application."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlsplit


def serve(application, ui_root, port):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, content_type='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(body)

        def handle_request(self, method):
            path = urlsplit(self.path).path
            try:
                if method=='GET' and path in ('/','/app.js','/interactions.js','/styles.css'):
                    name = {'/':'index.html','/app.js':'app.js','/interactions.js':'interactions.js','/styles.css':'styles.css'}[path]
                    content_type = {'/':'text/html','/app.js':'text/javascript','/interactions.js':'text/javascript','/styles.css':'text/css'}[path]
                    return self.respond(200,(ui_root/name).read_bytes(),content_type+'; charset=utf-8')
                if not path.startswith('/api/'):
                    return self.respond(404,b'{"error":"Not found"}')
                data = {}
                if method=='POST':
                    # No cross-origin mutation of the local research session.
                    origin = self.headers.get('Origin')
                    if origin and origin != 'http://'+self.headers.get('Host',''):
                        return self.respond(403,b'{"error":"Origin rejected"}')
                    length = int(self.headers.get('Content-Length','0'))
                    if length > 65536:
                        raise ValueError('Request too large')
                    def invalid_constant(value):
                        raise ValueError('Non-finite JSON number: '+value)
                    data = json.loads(self.rfile.read(length) or b'{}',parse_constant=invalid_constant)
                    if not isinstance(data,dict):
                        raise ValueError('JSON object required')
                result = application.route(method,path,data)
                self.respond(200,json.dumps(result,ensure_ascii=False,allow_nan=False).encode())
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                self.respond(400,json.dumps({'error':str(exc)},ensure_ascii=False).encode())

        def do_GET(self):
            self.handle_request('GET')

        def do_POST(self):
            self.handle_request('POST')

    server = HTTPServer(('127.0.0.1',port),Handler)
    print(f'Parking research workspace: http://127.0.0.1:{port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

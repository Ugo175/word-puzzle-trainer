#!/usr/bin/env python3
"""Serve Tile Club locally using the same engine as the command-line tool."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from game import Rounds, solutions
from trainer import load_words, DEFAULT_DICTIONARY

STATIC = Path(__file__).with_name('web')
MAX_REQUEST = 2 * 1024 * 1024
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
          '/favicon.svg': ('favicon.svg', 'image/svg+xml')}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def json(self, status, value):
        self.reply(status, json.dumps(value).encode('utf-8'))

    def local_request(self):
        # This development server is intentionally loopback-only. Reject foreign web origins.
        host = self.headers.get('Host', '')
        expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        return host in expected and self.headers.get('Origin', f'http://{host}') == f'http://{host}'

    def do_GET(self):
        if not self.local_request():
            self.json(403, {'error': 'Use the local server URL.'})
            return
        path = urlsplit(self.path).path
        if path not in ASSETS:
            self.json(404, {'error': 'Not found.'})
            return
        filename, content_type = ASSETS[path]
        self.reply(200, (STATIC / filename).read_bytes(), content_type)

    def do_POST(self):
        if not self.local_request():
            self.json(403, {'error': 'Use the local server URL.'})
            return
        if self.path not in ('/api/solve', '/api/round/start', '/api/round/guess', '/api/round/finish'):
            self.json(404, {'error': 'Not found.'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.json(415, {'error': 'Send application/json.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_REQUEST:
                self.json(413, {'error': 'Request must contain 1 byte to 2 MiB.'})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object.')
            if self.path == '/api/solve':
                result = {'rack': payload.get('rack'), 'words': solutions(payload.get('rack'), self.server.dictionary, payload.get('minimum', 2)), 'dictionary_size': len(self.server.dictionary)}
            elif self.path == '/api/round/start':
                result = self.server.rounds.start(payload.get('rack'), payload.get('seconds', 60), payload.get('minimum', 2))
            else:
                result = self.server.rounds.act(payload.get('id'), payload.get('word'), self.path.endswith('/finish'))
            self.json(200, result)
        except (ValueError, UnicodeError) as error:
            self.json(400, {'error': str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--dictionary', type=Path, default=DEFAULT_DICTIONARY)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535.')
    try:
        dictionary = load_words(args.dictionary)
        with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
            server.dictionary = dictionary
            server.rounds = Rounds(dictionary)
            print(f'Tile Club is ready at http://127.0.0.1:{args.port}', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f'Could not start the server: {error}\n')


if __name__ == '__main__':
    main()

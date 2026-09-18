#!/usr/bin/env python3
"""Локальный раздатчик для замеров: тот же http.server, но с явным charset=utf-8
в заголовке Content-Type (иначе chromium в песочнице декодирует UTF-8 как cp1252)."""
import functools, http.server, socketserver, sys

class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.html': 'text/html; charset=utf-8',
                      '.css': 'text/css; charset=utf-8',
                      '.js': 'text/javascript; charset=utf-8',
                      '.svg': 'image/svg+xml; charset=utf-8'}
    def log_message(self, *a): pass

port = int(sys.argv[1])
with socketserver.ThreadingTCPServer(('0.0.0.0', port), functools.partial(H, directory=sys.argv[2])) as srv:
    srv.allow_reuse_address = True
    srv.serve_forever()

# XXX FIXME currently LOG INFO is still displayed
# do not log INFO messages from mock server
import logging
logging.getLogger("wsgiref").setLevel(logging.WARNING)
from wsgiref import simple_server

import immutables

from conf import TOWEL_CONF


class MockApp(object):
    def __init__(self, monkey_map):
        self.route_map = {'/%s' % k: v for (k, v) in monkey_map.iteritems()}

    def __call__(self, environ, start_response):
        status = '200 OK'
        try:
            handler = self.route_map[environ['PATH_INFO']]
        except KeyError:
            handler = lambda: "Function has not been mocked!"

        response_body = str(handler())
        response_headers = [('Content-Type', 'text/plain'),
                            ('Content-Length', str(len(response_body)))]

        start_response(status, response_headers)
        return [response_body]


def main():
    app = MockApp(immutables.REPLACE_MODULES)
    mock_address = TOWEL_CONF.get('mock_server', 'address')
    mock_port = TOWEL_CONF.getint('mock_server', 'port')
    httpd = simple_server.make_server(mock_address, mock_port, app)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

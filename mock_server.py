class MockApp(object):
    def __init__(self, monkey_map):
        self.route_map = {'/%s' % k: v for (k, v) in monkey_map.iteritems()}

    def __call__(self, environ, start_response):
        status = '200 OK'
        try:
            handler = self.route_map[environ['PATH_INFO']]
        except KeyError:
            handler = lambda: "No such path"

        response_body = str(handler())
        response_headers = [('Content-Type', 'text/plain'),
                            ('Content-Length', str(len(response_body)))]

        start_response(status, response_headers)
        return [response_body]

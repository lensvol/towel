"""
This module monkey_patches functions that usually produce random output in an
attempt to receive a fixed diff-comparable representation
"""

import datetime
import importlib
import random
import requests
import urlparse
import uuid


def time_generator():
    TIME_SEED = 4242424242
    TIME_DELTA = 42
    last = TIME_SEED
    while True:
        last += TIME_DELTA
        yield last


def id_generator():
    ID_SEED = 42
    random.seed(ID_SEED)
    while True:
        bytes = [chr(random.randrange(256)) for i in range(16)]
        last = uuid.UUID(bytes=bytes, version=4)
        yield last


TIME_GENERATOR = time_generator()
ID_GENERATOR = id_generator()


def _time_from_seconds(seconds_str):
    seconds = int(seconds_str)
    return (datetime.datetime.fromtimestamp(0) +
            datetime.timedelta(seconds=seconds))


_monkey_map = {"oslo_utils.timeutils.utcnow": (TIME_GENERATOR.next,
                                               _time_from_seconds),
               "uuid.uuid4": (ID_GENERATOR.next, uuid.UUID)}

REPLACE_MODULES = {k.split('.')[-1]: v[0] for (k, v)
                   in _monkey_map.iteritems()}
POSTFETCH_HANDLERS = {k: v[1] for (k, v)
                      in _monkey_map.iteritems()}


def perform_monkey_patch(mock_server_url):
    """
    Each method instead of calling a mocked version performs a GET
    to the Mock Server.
    It has to be done in spite of eventlet-based nature of glance's services
    start to guarantee fixed order od uuid generation and timestamps.
    """
    class MockCall(object):
        def __init__(self, endpoint, proc_func):
            self.endpoint = endpoint
            self.proc_func = proc_func

        def __call__(self):
            data = requests.get(self.endpoint)
            return self.proc_func(data.text)

    for str_func in _monkey_map:
        mod_parts = str_func.split('.')
        module = importlib.import_module('.'.join(mod_parts[:-1]))
        func, proc_func = _monkey_map[str_func]
        func_endpoint = urlparse.urljoin(mock_server_url, mod_parts[-1])
        setattr(module, mod_parts[-1], MockCall(func_endpoint, proc_func))

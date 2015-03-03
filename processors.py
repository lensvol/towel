import collections
import json

import exc


class TextProcessor(object):
    """a class to process returned text based on content-type"""
    def __init__(self, content_type):
        self.content_type = content_type

    def process(self, text):
        raise NotImplementedError()

    def normalize(self, data):
        return data


class JsonTextProcessor(TextProcessor):
    def __init__(self):
        super(JsonTextProcessor, self).__init__(content_type='application/json')

    def process(self, text):
        try:
            data = json.loads(text)
            normalized = self.normalize(data)
            return json.dumps(normalized)
        except:
            raise exc.TowelError("Not a valid JSON")

    def normalize(self, data):
        if isinstance(data, dict):
            result = collections.OrderedDict()
            for k in sorted(data.keys()):
                result[k] = (self._normalize(data[k])
                             if isinstance(data[k], dict) else data[k])
            return result


class TextProcessorFactory(object):
    _map = {'application/json': JsonTextProcessor}

    def get(self, type):
        try:
            return self._map[type]()
        except:
            raise exc.TowelError("Content-Type '%s' not supported")

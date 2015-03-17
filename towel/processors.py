import collections
import json
from lxml import etree, html

import exc


class TextProcessor(object):
    """a class to process returned text based on content-type"""
    def __init__(self, content_type="text/html"):
        self.content_type = content_type

    def process(self, text):
        """
        Transferes text from response to a text in normalized form.
        The output is required to be comparable line-by-line by diff.
        """
        doc_root = html.fromstring(text)
        return etree.tostring(doc_root, encoding='unicode',
                              pretty_print=True)


class JsonTextProcessor(TextProcessor):
    def __init__(self):
        super(JsonTextProcessor, self).__init__(content_type='application/json')

    def process(self, text):
        try:
            data = json.loads(text)
            normalized = self.normalize(data)
            return json.dumps(normalized, indent=2)
        except:
            raise exc.BadTextData("Not a valid JSON")

    def normalize(self, data):
        if isinstance(data, dict):
            result = collections.OrderedDict()
            for k in sorted(data.keys()):
                result[k] = (self._normalize(data[k])
                             if isinstance(data[k], dict) else data[k])
            return result
        else:
            # for other non-dict valid json values (like lists)
            return data


class TextProcessorFactory(object):
    _map = {'application/json': JsonTextProcessor,
            'text/html': TextProcessor}

    def get(self, type):
        try:
            return self._map[type]()
        except KeyError as e:
            raise exc.TowelError("Content-Type '%s' not supported" %
                                 e.message)

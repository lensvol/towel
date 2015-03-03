#! /usr/bin/env python

import collections
import difflib
import os
import requests
import sys
import tempfile
import urlparse

from lxml import etree

from exc import TowelError
import processors


class Request(object):
    def __init__(self, type, url, **kwargs):
        self.type = type.lower()
        if self.type not in ["get", "post", "put"]:
            raise TowelError("Invalid method %s" % type)
        self.url = url
        self.args = dict(kwargs)

    def send(self):
        return getattr(self, "_" + self.type)()

    def _get(self):
        res = requests.get(self.url, **self.args)
        c_type = res.headers["content-type"]
        # FIXME think how to do it in less clumsy way
        c_type = c_type.split(';')[0]
        return (res.status_code, res.text, c_type)


class TowelProcessor(object):
    def __init__(self, filename, server_address):
        self.filename = filename
        self.server = server_address
        self.default_content_type = "application/json"
        self.proc_factory = processors.TextProcessorFactory()
        self.run()

    def run(self):
        tree = etree.parse(self.filename)
        for i, r_data in enumerate(tree.xpath("request")):
            other_args = dict((k, v) for (k, v) in r_data.items()
                              if k not in ["method", "url", "result"])
            result = r_data.get("result")
            content_type = other_args.get("content-type",
                                          self.default_content_type)
            request = Request(type=r_data.get("method"),
                              url=urlparse.urljoin(self.server,
                                                   r_data.get("url")),
                              **other_args)
            status, data, c_type = request.send()
            # FIXME add comparison for status_code, content_type
            processor = self.proc_factory.get(c_type.lower())
            actual = processor.process(data)
            expected = result if os.path.exists(result) else None
            self._compare(expected, actual, result)

    def _normalize(self, data):
        if isinstance(data, dict):
            result = collections.OrderedDict()
            for k in sorted(data.keys()):
                result[k] = (self._normalize(data[k])
                             if isinstance(data[k], dict) else data[k])
            return result

    def _compare(self, expected, actual, filename):
        """
        Perform comparison and print all diff information
        """
        expected = expected or ""
        tmp_file = filename + '.tmp'
        with open(tmp_file, 'w') as f:
            f.write(actual)
        with open(tmp_file, 'r') as f:
            diff = difflib.unified_diff(expected, f.readlines())
            for line in diff:
                sys.stdout.write(line)

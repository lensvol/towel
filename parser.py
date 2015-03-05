#! /usr/bin/env python

import collections
import difflib
import logging
import os
import requests
import sys
import urlparse

from lxml import etree

import exc
import processors


LOG = logging.getLogger("TowelProcessor")
LOG.setLevel(logging.INFO)
# add stdout handler to see progress
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
LOG.addHandler(ch)


class Request(object):
    def __init__(self, type, url, **kwargs):
        self.test_dir = kwargs.get("test_dir", "towel-tests")
        self.type = type.lower()
        self.is_system = self.type == "setup"
        if self.type not in ["get", "post", "setup"]:
            raise exc.TowelError("Invalid method %s" % type)
        self.url = url
        # for PUT and POST requests ->
        self.request_data = None
        self.request_file = kwargs.get("request-data")
        if self.request_file:
            with open(os.path.join(self.test_dir, self.request_file)) as f:
                self.request_data = f.read()
        self.request_content_type = kwargs.get("request-content-type",
                                               "application/json")
        self.args = dict(kwargs)

    def send(self):
        return getattr(self, "_" + self.type)()

    def _get(self):
        res = requests.get(self.url)
        c_type = res.headers["content-type"]
        return (res.status_code, res.text, c_type.lower())

    def _post(self):
        res = requests.post(self.url, data=self.request_data,
                            headers={'Content-Type': self.request_content_type})
        c_type = res.headers["content-type"]
        return (res.status_code, res.text, c_type.lower())

    def _setup(self):
        """
        A special endpoint to execute custom logic.
        The logic is stored in request-data file
        """
        # if no file with rules is given, perform nothing
        if not self.request_data:
            LOG.warn("No file given in setup call, ignoring it.")
            return
        xterm = ["xterm", "-e", "bash",
                 os.path.join(self.test_dir, self.request_file)]
        # FIXME Oh my, that's awful, time for bloody tears
        import subprocess
        import time
        proc = subprocess.Popen(xterm)
        time.sleep(5)
        if proc.poll() != 0:
            time.sleep(35)


class TowelProcessor(object):
    TOWEL_TEST_FILE = "towel.xml"
    TOWEL_TMP_SUFFIX = ".tmp"

    def __init__(self, test_dir, server_address):
        self.test_dir = test_dir
        self.filename = os.path.join(test_dir, self.TOWEL_TEST_FILE)
        self.server = server_address
        self.default_content_type = "text/html"
        self.default_status = 200
        self.proc_factory = processors.TextProcessorFactory()
        self.ok_tests = []
        self.failed_tests = []

    def fixate(self):
        """
        Moves actual responses 'response.tmp' into 'response'
        """
        # FIXME let's make it a blunt way at first, later some validation
        # against towel.xml may be added
        for f in os.listdir(self.test_dir):
            f = os.path.join(self.test_dir, f)
            if f.endswith(self.TOWEL_TMP_SUFFIX):
                os.rename(f, f[0:-4])

    def run(self):
        # check for file existance
        if not os.path.exists(self.filename):
            LOG.warn("No %s found, ignoring run command" % self.TOWEL_TEST_FILE)
        tree = etree.parse(self.filename)
        for i, r_data in enumerate(tree.xpath("request"), 1):
            LOG.info("-----Running test %d-----" % i)
            error = None
            other_args = dict((k, v) for (k, v) in r_data.items()
                              if k not in ["method", "url", "result"])
            result = r_data.get("result")
            if result:
                result = os.path.join(self.test_dir, result)
            content_type_exp = other_args.get("content-type",
                                              self.default_content_type)
            status_exp = int(other_args.get("status", self.default_status))
            request = Request(type=r_data.get("method"),
                              url=urlparse.urljoin(self.server,
                                                   r_data.get("url")),
                              test_dir=self.test_dir,
                              **other_args)
            data = request.send()
            if request.is_system:
                # nothing to do here
                continue
            status, data, content_type = data
            # FIXME think of a better way to compare
            # 'application/json; charset=utf-8' and 'application/json'
            content_type = content_type.split(';')[0]
            # if status_code or content_type doesn't match, no need to go
            # further
            if status_exp != status:
                error = "Expected %s status, got %s" % (status_exp, status)
            if content_type_exp != content_type:
                error = "Expected content-type %s, got %s" % (content_type_exp,
                                                              content_type)
            if error:
                self._print_fail(error)
                continue
            processor = self.proc_factory.get(content_type_exp)
            try:
                actual = processor.process(data)
            except exc.BadTextData as e:
                self._print_fail(e.message)
                continue
            expected = None
            if os.path.exists(result):
                with open(result) as f:
                    expected = f.readlines()
            res, diff = self._compare(expected, actual, result)
            if not res:
                self._print_fail("Expected response is different from actual",
                                 diff)
            else:
                self._print_ok()

    def _print_fail(self, reason, info=""):
        LOG.info("FAIL: %s\n%s" % (reason, info))

    def _print_ok(self):
        LOG.info("OK")

    def _normalize(self, data):
        if isinstance(data, dict):
            result = collections.OrderedDict()
            for k in sorted(data.keys()):
                result[k] = (self._normalize(data[k])
                             if isinstance(data[k], dict) else data[k])
            return result

    def _compare(self, expected, actual, filename):
        """
        Perform comparison and returns (bool success, str diff).
        'Success' is a flag indicating if expected == actual, 'diff'
        is '' in case of success or a text diff in case of failure.
        """
        expected = expected or ""
        tmp_file = filename + self.TOWEL_TMP_SUFFIX
        with open(tmp_file, 'w') as f:
            f.write(actual)
        with open(tmp_file, 'r') as f:
            diff = difflib.unified_diff(expected, f.readlines())
        text_diff = "\n".join(diff)
        # in case of success remove temporary file
        status = text_diff == ''
        if status:
            os.remove(tmp_file)
        return (status, text_diff)

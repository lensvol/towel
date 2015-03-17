#! /usr/bin/env python

import difflib
import logging
import os
import requests
import subprocess
import sys
import urlparse

from lxml import etree

import exc
import processors


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
# add stdout handler to see progress
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
LOG.addHandler(ch)


class Request(object):
    TYPES = ["get", "post", "setup"]

    def __init__(self, **kwargs):
        self.test_dir = kwargs.get("test_dir", "towel-tests")
        self.method = kwargs["method"].lower()
        if self.method not in Request.TYPES:
            raise exc.TowelError("Invalid method %s" % self.method)
        self.url = kwargs.get("url")
        self.help_str = kwargs.get("help")
        self.result_file = kwargs.get("result")
        # for PUT and POST requests ->
        self.request_data = None
        self.request_file = kwargs.get("request-data")
        if self.request_file:
            with open(self.request_file) as f:
                self.request_data = f.read()
        self.request_content_type = kwargs.get("request-content-type",
                                               "application/json")
        self.args = dict(kwargs)

    @property
    def is_system(self):
        return self.method == "setup"

    def send(self):
        return getattr(self, "_" + self.method)()

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
        A special endpoint to execute custom logic stored in request-data file
        """
        # if no file with rules is given, perform nothing
        if not self.request_data:
            LOG.warn("No file given in setup call, ignoring it.")
            return
        xterm = ["xterm", "-e", "bash", self.request_file]
        subprocess.call(xterm)

    def __str__(self):
        return ("Setup script <%s>" % self.request_file if self.is_system
                else "Testcase <%s>" % (self.help_str or self.result_file))


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
        for f in [f for f in os.listdir(self.test_dir)
                  if f.endswith(self.TOWEL_TMP_SUFFIX)]:
            f = os.path.join(self.test_dir, f)
            os.rename(f, f[0:-4])

    def _fix_relative(self, req_data):
        """
        Returns a dictionary containing absolute urls/file paths
        as well as other, non changed, request data
        """
        result = dict(req_data.items())
        relative_file_keys = ["result", "request-data"]
        relative_url_keys = ["url"]
        for k in relative_file_keys:
            if k in result:
                result[k] = os.path.join(self.test_dir, result[k])
        for k in relative_url_keys:
            if k in result:
                result[k] = urlparse.urljoin(self.server, result[k])
        return result

    def run(self):
        # check for file existance
        if not os.path.exists(self.filename):
            LOG.warn("No %s found, ignoring run command" % self.TOWEL_TEST_FILE)
        tree = etree.parse(self.filename)
        test_num = 0
        for r_data in tree.xpath("request"):
            r_data = self._fix_relative(r_data)
            result_filename = r_data.get("result")
            content_type_exp = r_data.get("content-type",
                                          self.default_content_type)
            status_exp = int(r_data.get("status", self.default_status))
            request = Request(test_dir=self.test_dir, **r_data)
            if request.is_system:
                self._print_run_data("Running %s" % request)
                request.send()
                continue
            test_num += 1
            self._print_run_data("Running %s #%d" % (request, test_num))
            status, data, content_type = request.send()
            # FIXME think of a better way to compare
            # 'application/json; charset=utf-8' and 'application/json'
            content_type = content_type.split(';')[0]
            # if status_code or content_type doesn't match, no need to go
            # further
            if not self._compare_result(content_type_exp, content_type,
                                        status_exp, status, data):
                continue
            processor = self.proc_factory.get(content_type_exp)
            try:
                actual = processor.process(data)
            except exc.BadTextData as e:
                self._print_fail(e.message)
                continue
            # save received data in tmp file
            tmp_file = result_filename + self.TOWEL_TMP_SUFFIX
            with open(tmp_file, 'w') as f:
                f.write(actual)
            # perform comparison of 2 files and print results
            res, diff = self._compare_files(result_filename, tmp_file)
            if not res:
                self._print_fail("Expected response is different from actual",
                                 diff)
            else:
                self._print_ok()

    def _print_run_data(self, data):
        LOG.info("-----%s-----" % data)

    def _print_fail(self, reason, info=""):
        LOG.info("FAIL: %s\n%s" % (reason, info))

    def _print_ok(self):
        LOG.info("OK")

    def _compare_files(self, expected, actual):
        """
        Performs comparison of 2 files and returns (bool success, str diff).
        'Success' is a flag indicating if expected == actual, 'diff'
        is '' in case of success or a text diff in case of failure.
        """
        # if no test has been run, then no expected file can be found
        if os.path.exists(expected):
            with open(expected) as f:
                exp_data = f.readlines()
        else:
            exp_data = ""
        # now compare expected_data with data from temporary file
        with open(actual) as f_act:
            act_data = f_act.readlines()
            diff = difflib.unified_diff(exp_data, act_data)
        text_diff = "\n".join(diff)
        # in case of success remove temporary file
        status = text_diff == ''
        if status:
            os.remove(actual)
        return (status, text_diff)

    def _compare_result(self, status_exp, status_act,
                        content_type_exp, content_type_act, data):
        """
        Returns True if content_type/status match expected ones,
        False otherwise. Outputs error messages in case of comparison failure.
        """
        error = None
        if status_exp != status_act:
            error = "Expected %s status, got %s" % (status_exp, status_act)
        if content_type_exp != content_type_act:
            error = "Expected content-type %s, got %s" % (content_type_exp,
                                                          content_type_act)
        if error:
            self._print_fail(error)
            # log received result -> do not save in a file.out.tmp
            self._print_fail("Actual response (won't be saved)", data)
            return False
        return True

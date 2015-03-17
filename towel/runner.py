#! /usr/bin/env python

import difflib
import logging
import os
import subprocess
import sys
import urlparse

import requests
from lxml import etree
from towel import processors, exc


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
        A special endpoint to execute custom logic stored in request-data file
        """
        # if no file with rules is given, perform nothing
        if not self.request_data:
            LOG.warn("No file given in setup call, ignoring it.")
            return
        xterm = ["xterm", "-e", "bash",
                 os.path.join(self.test_dir, self.request_file)]
        subprocess.call(xterm)


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
        Moves actual responses 'response.tmp' into 'response'.
        """
        # FIXME let's make it a blunt way at first, later some validation
        # against towel.xml may be added
        for f in [f for f in os.listdir(self.test_dir)
                  if f.endswith(self.TOWEL_TMP_SUFFIX)]:
            f = os.path.join(self.test_dir, f)
            os.rename(f, f[0:-4])

    def run(self):
        # check for file existance
        if not os.path.exists(self.filename):
            LOG.warn("No %s found, ignoring run command" % self.TOWEL_TEST_FILE)
        tree = etree.parse(self.filename)
        test_num = 0
        for r_data in tree.xpath("request"):
            other_args = dict((k, v) for (k, v) in r_data.items()
                              if k not in ["method", "url", "result"])
            result_filename = r_data.get("result")
            if result_filename:
                result_filename = os.path.join(self.test_dir, result_filename)
            content_type_exp = other_args.get("content-type",
                                              self.default_content_type)
            status_exp = int(other_args.get("status", self.default_status))
            request = Request(type=r_data.get("method"),
                              url=urlparse.urljoin(self.server,
                                                   r_data.get("url")),
                              test_dir=self.test_dir,
                              **other_args)
            if request.is_system:
                self._print_run_data("Running setup script '%s'" %
                                     request.request_file)
                request.send()
                continue
            test_num += 1
            self._print_run_data("Running test %d" % test_num)
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

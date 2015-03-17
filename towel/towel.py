#! /usr/bin/env python
import argparse
import os
import subprocess
import sys

from conf import TOWEL_CONF
import exc
import runner


"""
towel run 'some_dir'

Looks for towel.xml in 'some_dir', then runs towel tests one by one.
If the response file for a test exists, then the actual result is compared
with the saved response (stored in a file).

If the comparison fails for some reason or no previous response has been
recorded, then 'expected-response-file'.tmp will be created where the actual
response will be stored.


towel fixate 'some_dir'

Makes actual responses the expected ones.
No rocket science here: copies 'expected-response-file'.tmp into
'expected-response-file' and removes temporary ones.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=['run', 'fixate'])
    parser.add_argument('dirname', type=str)
    parser.add_argument('-a', '--address', type=str,
                        default='http://127.0.0.1')
    parser.add_argument('-p', '--port', type=int, default=9292)
    parsed = parser.parse_args(sys.argv[1:])
    mock_server_enabled = TOWEL_CONF.get('mock_server', 'enabled')
    # start Mock Server
    if mock_server_enabled:
        mock_server = subprocess.Popen(['python',
                                        'towel/start_mock_server.py'])
    towel_dir = os.path.join(parsed.dirname)
    try:
        if os.path.exists(towel_dir):
            tp = runner.TowelProcessor(
                towel_dir,
                server_address="%s:%d" % (parsed.address, parsed.port))
            getattr(tp, parsed.command)()
    except Exception as e:
        raise exc.TowelError("An error has occured: %s" % e.message)
    finally:
        if mock_server_enabled:
            # stop mock server
            mock_server.kill()


if __name__ == "__main__":
    main()

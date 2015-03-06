#! /usr/bin/env python
import argparse
import os
import sys

from runner import TowelProcessor


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
    towel_dir = os.path.join(parsed.dirname)
    if os.path.exists(towel_dir):
        tp = TowelProcessor(towel_dir,
                            server_address="%s:%d" % (parsed.address,
                                                      parsed.port))
        getattr(tp, parsed.command)()


if __name__ == "__main__":
    main()

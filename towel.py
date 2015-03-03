#! /usr/bin/env python
import argparse
import os
import sys

from parser import TowelProcessor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=['run', 'fixate'])
    parser.add_argument('dirname', type=str)
    parser.add_argument('-a', '--address', type=str,
                        default='http://127.0.0.1')
    parser.add_argument('-p', '--port', type=int, default=9292)
    parsed = parser.parse_args(sys.argv[1:])
    towel_main = os.path.join(parsed.dirname, "towel.xml")
    if os.path.exists(towel_main):
        parser = TowelProcessor(
            towel_main, server_address="%s:%d" % (parsed.address,
                                                  parsed.port))

if __name__ == "__main__":
    main()

"""
This module monkey_patches functions that usually produce random output in an
attempt to receive a fixed diff-comparable representation
"""

import datetime
import importlib


LOG_FILE = "log.file"


def time_generator():
    TIME_SEED = 4242424242
    TIME_DELTA = 42
    last = TIME_SEED
    while True:
        last += TIME_DELTA
        date = (datetime.datetime.fromtimestamp(0) +
                datetime.timedelta(seconds=last))
        with open(LOG_FILE, "a+") as f:
            f.write(str(date) + "\n")
        yield date


def id_generator():
    ID_SEED = 42
    import random
    random.seed(ID_SEED)
    from uuid import UUID
    while True:
        bytes = [chr(random.randrange(256)) for i in range(16)]
        last = UUID(bytes=bytes, version=4)
        with open(LOG_FILE, "a+") as f:
            f.write(str(last) + "\n")
        yield last


TIME_GENERATOR = time_generator()
ID_GENERATOR = id_generator()

_monkey_map = {"oslo_utils.timeutils.utcnow": TIME_GENERATOR.next,
               "uuid.uuid4": ID_GENERATOR.next}

_restore_map = {}


def perform_monkey_patch():
    import os
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    for str_func in _monkey_map:
        mod_parts = str_func.split('.')
        module = importlib.import_module('.'.join(mod_parts[:-1]))
        orig_func = getattr(module, mod_parts[-1])
        _restore_map[str_func] = orig_func
        setattr(module, mod_parts[-1], _monkey_map[str_func])


def restore_after_monkey_patch():
    for str_func in _restore_map:
        mod_parts = str_func.split('.')
        module = importlib.import_module('.'.join(mod_parts[:-1]))
        setattr(module, mod_parts[-1], _restore_map[str_func])

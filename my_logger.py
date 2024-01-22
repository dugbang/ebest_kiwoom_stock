import json
import logging.config

"""
로깅 수준
CRITICAL; 50
ERROR; 40
WARNING; 30
INFO; 20
DEBUG; 10
NOTSET; 0

The logging module is thread-safe; it handles the locking for you.
https://docs.python.org/2/library/logging.html#thread-safety
"""

with open('logging.json', 'r', encoding='UTF-8') as f_:
    logging.config.dictConfig(json.load(f_))

logger = logging.getLogger('file')
# logger.setLevel(logging.CRITICAL)
# logger.setLevel(logging.ERROR)
# logger.setLevel(logging.WARNING)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

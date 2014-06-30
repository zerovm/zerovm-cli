#  Copyright 2014 Rackspace, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging

__version__ = '0.2'


class ZPMException(Exception):
    """
    Basic exception to signal ZPM-specific errors. Useful for cases in which an
    exception must be differentiated from the more general built-in exception
    types.
    """


def get_logger(name):
    log = logging.getLogger(name)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(
        logging.Formatter(fmt='%(levelname)s:%(name)s: %(message)s')
    )
    log.addHandler(_stream_handler)
    return log

LOG_LEVEL_MAP = dict(
    debug=logging.DEBUG,
    info=logging.INFO,
    warning=logging.WARNING,
    error=logging.ERROR,
    critical=logging.CRITICAL,
)

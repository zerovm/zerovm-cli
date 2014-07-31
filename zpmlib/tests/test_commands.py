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

import mock

from zpmlib import commands
from swiftclient.exceptions import ClientException


def test_all_commands_sorted():
    cmd_names = [cmd.__name__ for cmd in commands.all_commands()]
    assert cmd_names == sorted(cmd_names)


def test_swift_log_filter():
    log_filter = commands.SwiftLogFilter()

    record = mock.Mock()
    record.levelname = 'INFO'

    filtered_record = mock.Mock()
    filtered_record.levelname = 'ERROR'
    filtered_record.msg = ClientException('Container GET failed',
                                          http_status=404)

    assert log_filter.filter(record) is True
    assert log_filter.filter(filtered_record) is False

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

import os
import operator
from zpmlib import zpm


_commands = []


def command(func):
    _commands.append(func)
    return func


def all_commands():
    return sorted(_commands, key=operator.attrgetter('__name__'))


@command
def new(parser):
    """Create a new ZeroVM application workspace"""

    def cmd(args):
        zpm.create_project(args.dir)
        print('Created new project in "%s"' % args.dir)

    parser.add_argument('dir', help='Non-existent or empty directory',
                        metavar='WORKING_DIR', nargs='?',
                        default=os.getcwd())
    parser.set_defaults(func=cmd)


@command
def bundle(parser):
    """Bundle a ZeroVM application"""

    def cmd(args):
        zpm.bundle_project(args.dir)

    parser.add_argument('dir', help='ZeroVM workspace',
                        metavar='WORKING_DIR', nargs='?',
                        default=os.getcwd())
    parser.set_defaults(func=cmd)

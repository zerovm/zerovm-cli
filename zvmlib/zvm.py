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

import argparse
import sys

from zpmlib import commands
from zvshlib import zvsh


def set_up_arg_parser():
    # zpm already has some a nice arg parser and command config code,
    # so let's extend/reuse/abuse that.
    #
    # TODO(larsbutler): Extract this generic command arg code to a shared
    # common library?
    parser = commands.set_up_arg_parser()
    parser.description = 'ZeroVM command line utility'
    parser.epilog = ("See 'zvm <command> --help' for more information on a "
                     "specific command.")
    return parser


@commands.command
@commands.arg(
    'command',
    help=('Zvsh command, can be:\n'
          '- path to ZeroVM executable\n'
          '- "gdb" (for running debugger)\n'),
)
@commands.arg(
    '--zvm-image',
    help=('ZeroVM image file(s) in the following '
          'format:\npath[,mount point][,access type]\n'
          'defaults: path,/,ro\n'),
    action='append',
)
@commands.arg(
    '--zvm-debug',
    help='Enable ZeroVM debug output into zvsh.log\n',
    action='store_true',
)
@commands.arg(
    '--zvm-trace',
    help='Enable ZeroVM trace output into zvsh.trace.log\n',
    action='store_true',
)
@commands.arg(
    '--zvm-verbosity',
    help='ZeroVM debug verbosity level\n',
    type=int,
)
@commands.arg(
    '--zvm-getrc',
    help=('If set, zvsh will exit with '
          'zerovm return code and not the application one\n'),
    action='store_true',
)
@commands.arg(
    '--zvm-save-dir',
    help=('Save ZeroVM environment files into provided directory,\n'
          'directory will be created/re-created\n'),
    action='store',
)
@commands.arg(
    'cmd_args',
    help='command line arguments\n',
    nargs=argparse.REMAINDER,
)
def run(args):
    """Locally execute a ZeroVM application
    """
    # TODO(larsbutler): We drop the first item from argv, in case the `gdb`
    # option is invoked. The `zvshlib.zvsh.Shell._run_gdb` method expects there
    # to only be one base command (`zvsh`) to precede the rest of the args.
    # In this case, there are instead two: `zvm run`.
    # So we need to trim off `zvm` in order to keep the same behavior, without
    # changing the zvsh code.
    shell = zvsh.Shell(sys.argv[1:], args=args)
    shell.run()

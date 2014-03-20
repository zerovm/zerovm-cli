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
import json
import operator
import tarfile
import gzip
import shlex
import argparse
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from zpmlib import zpm, miniswift

# List of function that will be the top-level zpm commands.
_commands = []


def set_up_arg_parser():
    parser = argparse.ArgumentParser(
        description='ZeroVM Package Manager',
        epilog=("See 'zpm <command> --help' for more information on a specific"
                " command."),
    )
    subparsers = parser.add_subparsers(description='available subcommands',
                                       metavar='COMMAND')

    for cmd in all_commands():
        subparser = subparsers.add_parser(cmd.__name__, help=cmd.__doc__)
        # Add arguments in reverse order: the last decorator
        # (bottom-most in the source) is called first, so its
        # arguments will be at the front of the list.
        for args, kwargs in reversed(getattr(cmd, '_args', [])):
            subparser.add_argument(*args, **kwargs)
        subparser.set_defaults(func=cmd)

    return parser


def command(func):
    """Register `func` as a top-level zpm command.

    The name of the function will be the name of the command and any
    cmdline arguments registered with `arg` will be available.
    """
    _commands.append(func)
    return func


def arg(*args, **kwargs):
    """Decorator for adding command line argument.

    The `args` and `kwargs` will eventually be passed to
    `ArgumentParser.add_argument`.
    """
    def decorator(func):
        if not hasattr(func, '_args'):
            func._args = []
        func._args.append((args, kwargs))
        return func
    return decorator


def all_commands():
    return sorted(_commands, key=operator.attrgetter('__name__'))


@command
@arg('dir', help='Non-existent or empty directory',
     metavar='WORKING_DIR', nargs='?',
     default=os.getcwd())
def new(args):
    """Create a new ZeroVM application workspace"""

    zpm.create_project(args.dir)
    print('Created new project in "%s"' % args.dir)


@command
def bundle(args):
    """Bundle a ZeroVM application

    This command creates a ZAR using the instructions in ``zar.json``.
    The file is read from the project root.
    """
    root = zpm.find_project_root()
    zpm.bundle_project(root)


def _generate_job_desc(zar, swift_url):
    job = []

    def make_file_list(zgroup):
        file_list = []
        for device in zgroup['devices']:
            dev = {'device': device['name']}
            if 'path' in device:
                dev['path'] = device['path']
            file_list.append(dev)
        return file_list

    # TODO(mg): we should eventually reuse zvsh._nvram_escape
    def escape(value):
        for c in '\\", \n':
            value = value.replace(c, '\\x%02x' % ord(c))
        return value

    def translate_args(cmdline):
        cmdline = cmdline.encode('utf8')
        args = shlex.split(cmdline)
        return ' '.join(escape(arg.decode('utf8')) for arg in args)

    for zgroup in zar['execution']['groups']:
        jgroup = {'name': zgroup['name']}
        jgroup['exec'] = {
            'path': zgroup['path'],
            'args': translate_args(zgroup['args']),
        }

        jgroup['file_list'] = make_file_list(zgroup)
        jgroup['file_list'].append({'device': 'image', 'path': swift_url})
        job.append(jgroup)
    return job


@command
@arg('zar', help='A ZeroVM artifact')
@arg('target', help='Swift path (directory) to deploy into')
@arg('--execute', action='store_true', help='Immediatedly '
     'execute the deployed Zar (for testing)')
@arg('--os-auth-url', default=os.environ.get('OS_AUTH_URL'),
     help='OpenStack auth URL. Defaults to $OS_AUTH_URL.')
@arg('--os-tenant-name', default=os.environ.get('OS_TENANT_NAME'),
     help='OpenStack tenant. Defaults to $OS_TENANT_NAME.')
@arg('--os-username', default=os.environ.get('OS_USERNAME'),
     help='OpenStack username. Defaults to $OS_USERNAME.')
@arg('--os-password', default=os.environ.get('OS_PASSWORD'),
     help='OpenStack password. Defaults to $OS_PASSWORD.')
def deploy(args):
    """Deploy a ZeroVM application

    This deploys a zar onto Swift. The zar can be one you have
    downloaded or produced yourself :ref:`zpm-bundle`.

    You will need to know the Swift authentication URL, username,
    password, and tenant name. These can be supplied with command line
    flags (see below) or you can set the corresponding environment
    variables. The environment variables are the same as the ones used
    by the `Swift command line tool <http://docs.openstack.org/
    user-guide/content/swift_commands.html>`_, so if you're already
    using that to upload files to Swift, you will be ready to go.
    """
    print('deploying %s' % args.zar)

    tar = tarfile.open(args.zar)
    zar = json.load(tar.extractfile('zar.json'))

    #from pprint import pprint
    #print('loaded zar:')
    #pprint(zar)

    client = miniswift.ZwiftClient(args.os_auth_url,
                                   args.os_tenant_name,
                                   args.os_username,
                                   args.os_password)
    client.auth()

    path = '%s/%s' % (args.target, os.path.basename(args.zar))
    client.upload(path, gzip.open(args.zar).read())

    swift_path = urlparse.urlparse(client._swift_url).path
    if swift_path.startswith('/v1/'):
        swift_path = swift_path[4:]

    if args.execute:
        swift_url = 'swift://%s/%s' % (swift_path, path)
        job = _generate_job_desc(zar, swift_url)

        print('job template:')
        from pprint import pprint
        pprint(job)
        print('executing')
        client.post_job(json.dumps(job))

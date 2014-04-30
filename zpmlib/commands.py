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
import argparse

from zpmlib import zpm

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
        doclines = cmd.__doc__.splitlines()
        summary = doclines[0]
        description = '\n'.join(doclines[1:])
        subparser = subparsers.add_parser(cmd.__name__,
                                          help=summary,
                                          description=description)
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

    If `kwargs` has an `envvar` key, then the default value for the
    command line argument will be taken from the environment variable
    with this name.

    The default value is automatically added to the help string. We do
    it here instead of using argparse.ArgumentDefaultsHelpFormatter
    since we format the help in more than one place (cmdline and
    Sphinx doc).
    """
    envvar = kwargs.get('envvar')
    if envvar:
        del kwargs['envvar']
        # The default value is shown in the generated documentation.
        # We therefore only set it if we're not building the
        # documentation with tox.
        if '_TOX_SPHINX' not in os.environ:
            kwargs['default'] = os.environ.get(envvar)
        kwargs['help'] += ' (default: $%s)' % envvar
    else:
        if 'default' in kwargs:
            kwargs['help'] += ' (default: %s)' % kwargs['default']

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
     default='.')
def new(args):
    """Create template ``zapp.yaml`` file

    Create a default ZeroVM application ``zapp.yaml`` specification in the
    target directory. If no directory is specified, ``zapp.yaml`` will be
    created in the current directory.
    """

    try:
        zappyaml = zpm.create_project(args.dir)
    except RuntimeError as err:
        print(err)
    else:
        print("Created '%s'" % zappyaml)


@command
def bundle(args):
    """Bundle a ZeroVM application

    This command creates a Zapp using the instructions in ``zapp.yaml``.
    The file is read from the project root.
    """
    root = zpm.find_project_root()
    zpm.bundle_project(root)


@command
@arg('zapp', help='A ZeroVM application')
@arg('target', help='Deployment target (Swift container name)')
@arg('--execute', action='store_true', help='Immediatedly '
     'execute the deployed Zapp (for testing)')
@arg('--auth-version', '-V', default='1.0', choices=['1.0', '2.0'],
     help='Swift auth version')
@arg('--auth', '-A', envvar='ST_AUTH',
     help='(Auth v1.0) URL for obtaining an auth token')
@arg('--user', '-U', envvar='ST_USER',
     help='(Auth v1.0) User name for obtaining an auth token')
@arg('--key', '-K', envvar='ST_KEY',
     help='(Auth v1.0) Key for obtaining an auth token')
@arg('--os-auth-url', envvar='OS_AUTH_URL',
     help='(Auth v2.0) OpenStack auth URL')
@arg('--os-tenant-name', envvar='OS_TENANT_NAME',
     help='(Auth v2.0) OpenStack tenant')
@arg('--os-username', envvar='OS_USERNAME',
     help='(Auth v2.0) OpenStack username')
@arg('--os-password', envvar='OS_PASSWORD',
     help='(Auth v2.0) OpenStack password')
@arg('--no-ui-auth', action='store_true',
     help='Do not generate any authentication code for the web UI')
def deploy(args):
    """Deploy a ZeroVM application

    This deploys a zapp onto Swift. The zapp can be one you have
    downloaded or produced yourself :ref:`zpm-bundle`.

    You will need to know the Swift authentication URL, username,
    password, and tenant name. These can be supplied with command line
    flags (see below) or you can set the corresponding environment
    variables. The environment variables are the same as the ones used
    by the `Swift command line tool <http://docs.openstack.org/
    user-guide/content/swift_commands.html>`_, so if you're already
    using that to upload files to Swift, you will be ready to go.
    """
    print('deploying %s' % args.zapp)
    zpm.deploy_project(args)


@command
@arg('command', nargs='?', help='A zpm command')
def help(args):
    """Show this help"""
    parser = set_up_arg_parser()
    cmd_names = [c.__name__ for c in _commands]
    if args.command is None or args.command not in cmd_names:
        if args.command is not None:
            print('no such command: %s' % args.command)
        parser.print_help()
    else:
        parser.parse_args([args.command, '-h'])

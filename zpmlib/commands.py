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
import shlex
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from zpmlib import zpm, miniswift

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
        root = zpm.find_project_root()
        zpm.bundle_project(root)

    parser.set_defaults(func=cmd)


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
        args = shlex.split(cmdline)
        return ' '.join(escape(arg) for arg in args)

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
def deploy(parser):

    def cmd(args):
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
        client.upload(path, open(args.zar).read())

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

    parser.add_argument('zar', help='A ZeroVM artifact')
    parser.add_argument('target', help='Swift path (directory) to deploy into')
    parser.add_argument('--execute', action='store_true', help='Immediatedly '
                        'execute the deployed Zar (for testing)')
    parser.add_argument('--os-auth-url',
                        default=os.environ.get('OS_AUTH_URL'),
                        help='OpenStack auth URL. Defaults to $OS_AUTH_URL.')
    parser.add_argument('--os-tenant-name',
                        default=os.environ.get('OS_TENANT_NAME'),
                        help='OpenStack tenant. Defaults to $OS_TENANT_NAME.')
    parser.add_argument('--os-username',
                        default=os.environ.get('OS_USERNAME'),
                        help='OpenStack username. Defaults to $OS_USERNAME.')
    parser.add_argument('--os-password',
                        default=os.environ.get('OS_PASSWORD'),
                        help='OpenStack password. Defaults to $OS_PASSWORD.')

    parser.set_defaults(func=cmd)

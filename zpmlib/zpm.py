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
import tarfile
import glob
import gzip
import json
import shlex
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
try:
    import cStringIO as StringIO
except ImportError:
    import io as StringIO

from os import path
from zpmlib import miniswift

import jinja2

DEFAULT_ZAR_JSON = {
    "execution": {
        "groups": [
            {
                "path": "file://python2.7:python",
                "args": "",
                "name": "",
                "devices": [
                    {
                        "name": "python2.7"
                    },
                    {
                        "name": "stdout"
                    },
                ]
            }
        ]
    },
    "meta": {
        "Version": "",
        "name": "",
        "Author-email": "",
        "Summary": "",
    },
    "help": {
        "description": "",
    },
    "bundling": [
        ""
    ],
}


def create_project(location):
    """
    Create a ZeroVM application project by writing a default `zar.json` in the
    specified directory `location`.

    :returns: Full path to the created `zar.json` file.
    """
    if path.exists(location):
        if not path.isdir(location):
            # target must be an empty directory
            raise RuntimeError("Target `location` must be a directory")
    else:
        os.makedirs(location)
    return _create_zar_json(location)


def _create_zar_json(location):
    """
    Create a default `zar.json` file in the specified directory `location`.

    Raises a `RuntimeError` if the `location` already contains a `zar.json`
    file.
    """
    filepath = os.path.join(location, 'zar.json')
    if os.path.exists(filepath):
        raise RuntimeError("'%s' already exists!" % filepath)

    with open(os.path.join(location, 'zar.json'), 'w') as fp:
        json.dump(DEFAULT_ZAR_JSON, fp, indent=4)

    return filepath


def find_project_root():
    root = os.getcwd()
    while not os.path.isfile(os.path.join(root, 'zar.json')):
        oldroot, root = root, os.path.dirname(root)
        if root == oldroot:
            raise RuntimeError("no zar.json file found")
    return root


def _generate_job_desc(zar):
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
        job.append(jgroup)
    return job


def _add_ui(tar, zar):
    loader = jinja2.PackageLoader('zpmlib', 'templates')
    env = jinja2.Environment(loader=loader)

    for path in ['index.html', 'style.css', 'zebra.js']:
        tmpl = env.get_template(path)
        output = tmpl.render(zar=zar)
        info = tarfile.TarInfo(name=path)
        info.size = len(output)
        print('adding %s' % path)
        tar.addfile(info, StringIO.StringIO(output))


def bundle_project(root):
    """
    Bundle the project under root.
    """
    zar_json = os.path.join(root, 'zar.json')
    zar = json.load(open(zar_json))

    zar_name = zar['meta']['name'] + '.zar'

    tar = tarfile.open(zar_name, 'w:gz')

    job = _generate_job_desc(zar)
    job_json = json.dumps(job)
    info = tarfile.TarInfo(name='%s.json' % zar['meta']['name'])
    info.size = len(job_json)
    print('adding %s' % info.name)
    tar.addfile(info, StringIO.StringIO(job_json))

    zar['bundling'].append('zar.json')
    ui = zar.get('ui', [])
    for pattern in zar['bundling'] + ui:
        for path in glob.glob(os.path.join(root, pattern)):
            print('adding %s' % path)
            relpath = os.path.relpath(path, root)
            info = tarfile.TarInfo(name=relpath)
            info.size = os.path.getsize(path)
            tar.addfile(info, open(path, 'rb'))

    if not ui:
        _add_ui(tar, zar)

    tar.close()
    print('created %s' % zar_name)


def deploy_project(args):
    tar = tarfile.open(args.zar)
    zar = json.load(tar.extractfile('zar.json'))

    client = miniswift.ZwiftClient(args.os_auth_url,
                                   args.os_tenant_name,
                                   args.os_username,
                                   args.os_password)
    client.auth()

    path = '%s/%s' % (args.target, os.path.basename(args.zar))
    client.upload(path, gzip.open(args.zar).read())

    swift_path = urlparse.urlparse(client._swift_service_url).path
    if swift_path.startswith('/v1/'):
        swift_path = swift_path[4:]

    swift_url = 'swift://%s/%s' % (swift_path, path)
    job = json.load(tar.extractfile('%s.json' % zar['meta']['name']))
    device = {'device': 'image', 'path': swift_url}
    for group in job:
        group['file_list'].append(device)
    job_json = json.dumps(job)
    client.upload('%s/%s.json' % (args.target, zar['meta']['name']), job_json)

    # TODO(mg): inserting the username and password in the uploaded
    # file makes testing easy, but should not be done in production.
    # See issue #44.
    deploy = {'auth_url': args.os_auth_url,
              'tenant': args.os_tenant_name,
              'username': args.os_username,
              'password': args.os_password}
    for path in zar.get('ui', ['index.html', 'style.css', 'zebra.js']):
        # Upload UI files after expanding deployment parameters
        tmpl = jinja2.Template(tar.extractfile(path).read())
        output = tmpl.render(deploy=deploy)
        client.upload('%s/%s' % (args.target, path), output)

    if args.execute:
        print('job template:')
        from pprint import pprint
        pprint(job)
        print('executing')
        client.post_job(job)

    print('app deployed to\n  %s/%s/' % (client._swift_service_url,
                                         args.target))

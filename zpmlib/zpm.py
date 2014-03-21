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
import json
import shlex
try:
    import cStringIO as StringIO
except ImportError:
    import io as StringIO

from os import path

import jinja2


def create_project(location):
    """
    Create an empty project in the specified directory `location`.
    """
    if path.exists(location):
        if path.isdir(location) and len(os.listdir(location)) == 0:
            # if it's an empty dir, create the project
            _create_project(location)
        else:
            # target must be an empty directory
            raise RuntimeError("Location must be an empty directory")
    else:
        os.makedirs(location)
        _create_project(location)


def _create_project(location):
    """
    Actually create the directories and ini files for the project.
    """
    for proj_dir in ('data', 'lib', 'src'):
        os.makedirs(path.join(location, proj_dir))


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

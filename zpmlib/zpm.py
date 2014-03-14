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

from os import path

try:
    from configparser import ConfigParser
except ImportError:
    # Python 2 fallback
    from ConfigParser import ConfigParser


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


def bundle_project(root):
    """
    Bundle the project under root.
    """
    zar_json = os.path.join(root, 'zar.json')
    zar = json.load(open(zar_json))

    zar_name = zar['meta']['name'] + '.zar'

    tar = tarfile.open(zar_name, 'w:gz')

    for pattern in zar['bundling'] + ['zar.json']:
        for path in glob.glob(os.path.join(root, pattern)):
            print('adding %s' % path)
            relpath = os.path.relpath(path, root)
            info = tarfile.TarInfo(name=relpath)
            info.size = os.path.getsize(path)
            tar.addfile(info, open(path, 'rb'))
    tar.close()
    print('created %s' % zar_name)


def make_tar(tar_fp, path, arcpath):
    """
    Recursively pack the files at `path` into a tar file.

    :param tar_fp:
        A writable file-like.
    :param path:
        Directory or file to add the archive.
    :param arcpath:
        Path in the archive in which to place the files in `path`.
    """
    tar = tarfile.open(mode='w', fileobj=tar_fp)
    try:
        tar.add(path, arcname=arcpath)
    finally:
        tar.close()


def get_tars_from_zar_ini(zar_ini_fp):
    """
    Parse a zar.ini and get the paths of all the referenced tar files as a
    generator.

    Side effect: If the tar doesn't exist and there is a source path defined
    for the tar, we will attempt to create it.

    :raises:
        `RuntimeError` if the tar doesn't exist and there's no source defined
        from which it can be build.
    """
    zar_ini_cp = ConfigParser()
    zar_ini_cp.readfp(zar_ini_fp)
    # get [tars] info
    for name, mapping in zar_ini_cp.items('tars'):
        src_path, tar_path, mount_pt = mapping.split(':')
        if not path.exists(tar_path):
            if src_path == '':
                raise RuntimeError("Tar does not exist, and there's no source"
                                   "to build it from")
            else:
                # we have a source path, but the tar isn't there,
                # so build it
                with open(tar_path, 'w') as fp:
                    make_tar(fp, tar_path, path.basename(tar_path))
        yield tar_path

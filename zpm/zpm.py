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

from os import path
from ConfigParser import ConfigParser

META_INI_TEMPLATE = """\
[metadata]
name =
version =
summary =
author-email =
license =
"""
ZAR_INI_TEMPLATE = """\
[zar]
# The program to run inside ZeroVM. For example:
# program = python myscript.py arg1 arg2 arg3
program =
[tars]
# name = <path to unpacked src>:<path to tar file>:<mount point on the zvm fs>
# Examples:
# myapp = ./myapp:lib/myapp.tar:/lib/python2.7/site-packages
# python = :/path/to/python.tar:/
"""


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

    # make the template config files:
    with open(path.join(location, 'meta.ini'), 'w') as fh:
        fh.write(META_INI_TEMPLATE)

    with open(path.join(location, 'zar.ini'), 'w') as fh:
        fh.write(ZAR_INI_TEMPLATE)


def bundle_project(location):
    """
    Bundle the project given the root project directory as `location`.
    """
    location = path.abspath(location)

    zar_ini = path.join(location, 'zar.ini')
    meta_ini = path.join(location, 'meta.ini')

    # read zar.ini
    with open(zar_ini) as fp:
        tars = get_tars_from_zar_ini(fp)
        tars = list(tars)
    # TODO(LB): Maybe need a `zpm --bundle --recreate` to force recreation of
    # cached tars.

    # now bundle up all of those tars (by tar location specified in the zar.ini
    # into the .zar,
    # plus the zar.ini and meta.ini
    # use the dirname as the zar name
    zar_name = '%s.zar' % path.split(location)[1]
    zar = tarfile.open(name=zar_name, mode='w')
    try:
        for each_file in tars + [zar_ini, meta_ini]:
            zar.add(each_file, path.basename(each_file))
    finally:
        zar.close()
    # TODO(LB): Return or print the generated .zar filename?


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

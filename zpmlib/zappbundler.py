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
import subprocess

import zpmlib

LOG = zpmlib.get_logger(__name__)
_DEFAULT_BUNDLER = 'python'


def bundle(working_dir, zapp, tar, **kwargs):
    _BUNDLERS.get(zapp.get('project_type'),
                  _BUNDLERS.get(_DEFAULT_BUNDLER))(
        working_dir, zapp, tar, **kwargs
    )


def python_bundler(working_dir, zapp, tar, refresh_deps=False):
    # First, write the deps for tox to use:
    deps = zapp.get('dependencies', [])
    if len(deps) == 0:
        # Nothing extra to do
        return

    deps_file = os.path.join(working_dir, '.zapp', 'deps.txt')
    with open(deps_file, 'w') as fp:
        for dep in deps:
            if isinstance(dep, list):
                # the dependency was specified as a list, where the first item
                # is the name of the package (and the other items are
                # modules/packages installed by this python package which bear
                # a different name)
                fp.write('%s\n' % dep[0])
            else:
                fp.write('%s\n' % dep)

    tox_ini_path = os.path.join(working_dir, '.zapp', 'tox.ini')

    LOG.info("Fetching third party Python dependencies...")
    if refresh_deps:
        tox_cmd = 'tox -r -c %s' % tox_ini_path
    else:
        tox_cmd = 'tox -c %s' % tox_ini_path

    # NOTE(larsbutler): The following subprocess code could be replaced with
    # the following code:
    #
    #   try:
    #       subprocess.check_output(tox_cmd.split())
    #   except subprocess.CalledProcessError as err:
    #       raise zpmlib.ZPMException(err.output)
    #
    # However, `check_output` does not appear in the `subprocess` module until
    # Python 2.7. Therefore, in order in order to keep Python 2.6 support we
    # have to do this in a less clean way.
    # See
    # https://docs.python.org/2/library/subprocess.html#subprocess.check_output
    sp = subprocess.Popen(tox_cmd.split(), stdout=subprocess.PIPE)
    retcode = sp.wait()
    if not retcode == 0:
        stdoutdata, _stderrdata = sp.communicate()
        # If `check_output` returns with a non-zero error, raise up an
        # error with the output:
        raise zpmlib.ZPMException(stdoutdata)

    site_pkgs = os.path.join(
        working_dir,
        '.zapp/.zapp/venv/lib/python2.7/site-packages'
    )
    modules = os.listdir(site_pkgs)
    LOG.info("Bundling third party Python dependencies...")
    for dep in deps:
        # Sometimes a package can install multiple modules, with different
        # names, or the installed package/module is different from that of the
        # package name on PyPI.
        # In this case, we allow the user to specify the module/package names
        # to grab at bundle time.
        # For example: ["package_name", "module1", "package1"]
        # "package_name" is the name of the top-level python package. We would
        # install this with `pip install package_name`, for example.
        # If the `setup.py` for this package specifies that "module1" and
        # "package1" are installed
        # If the `setup.py` for this package specifies additional `packages` or
        # `py_modules`, we can specify to zpm to bundle these as well. The
        # example above will bundle "extramodule1" and "extrapackage1".
        if isinstance(dep, list):
            for subdep in dep[1:]:
                _python_bundle_dep(working_dir, tar, site_pkgs, modules,
                                   subdep)
        else:
            _python_bundle_dep(working_dir, tar, site_pkgs, modules, dep)


def _python_bundle_dep(working_dir, tar, site_pkgs_dir, modules_list, dep):
    from zpmlib import zpm

    if dep in modules_list:
        dep_path = os.path.join(site_pkgs_dir, dep)
    elif '%s.py' % dep in modules_list:
        dep_path = os.path.join(site_pkgs_dir, '%s.py' % dep)
    else:
        raise zpmlib.ZPMException(
            "Dependency '%s' not found! Try bundling again with the "
            "--refresh-deps option (`zpm bundle --refresh-deps`)."
            % dep
        )
    arcname = os.path.join('/lib/python2.7/site-packages',
                           os.path.basename(dep_path))
    zpm._add_file_to_tar(working_dir, dep_path, tar, arcname=arcname)


_BUNDLERS = {
    'python': python_bundler,
}

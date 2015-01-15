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
import shutil
import tarfile
import tempfile

import mock
import yaml

from zpmlib import zpm


def touch_file(dir_name, file_name):
    open(os.path.join(dir_name, file_name), 'w').close()


class TestPythonBundler:

    def test_bundle_no_deps(self):
        tempdir = tempfile.mkdtemp()

        try:
            zpm.create_project(tempdir, template='python')
            with open(os.path.join(tempdir, 'zapp.yaml')) as zapp_yaml:
                zapp = yaml.safe_load(zapp_yaml)

            # add some files to "bundling" section
            touch_file(tempdir, 'main.py')
            zapp['bundling'].append('main.py')

            # rewrite the zapp.yaml
            with open(os.path.join(tempdir, 'zapp.yaml'), 'w') as zapp_yaml:
                zapp_yaml.write(yaml.dump(zapp))

            zpm.bundle_project(tempdir)
            zapp_file = os.path.join(tempdir,
                                     os.path.basename(tempdir) + '.zapp')
            tar = tarfile.open(zapp_file)
            expected_file_names = [
                'boot/system.map',
                'zapp.yaml',
                'main.py',
            ]
            assert expected_file_names == [x.name for x in tar.getmembers()]
        finally:
            shutil.rmtree(tempdir)

    def test_bundle(self):
        tempdir = tempfile.mkdtemp()
        zapp_file = os.path.join(tempdir, os.path.basename(tempdir) + '.zapp')
        site_pkgs = os.path.join(tempdir, '.zapp/.zapp/venv/lib/python2.7/'
                                          'site-packages')
        try:
            zpm.create_project(tempdir, template='python')
            with open(os.path.join(tempdir, 'zapp.yaml')) as zapp_yaml:
                zapp = yaml.safe_load(zapp_yaml)

            # add some files to "bundling" section
            touch_file(tempdir, 'main.py')
            zapp['bundling'].append('main.py')

            # add dependencies:
            zapp['dependencies'] = [
                'dep1',
                'dep2',
                ['dontcare', 'foodep3'],
            ]

            # rewrite the zapp.yaml
            with open(os.path.join(tempdir, 'zapp.yaml'), 'w') as zapp_yaml:
                zapp_yaml.write(yaml.dump(zapp))

            ######################
            # Test normal bundling
            def tox_fetch_deps(*args, **kwargs):
                # fake creating a venv and installing deps with tox
                os.makedirs(site_pkgs)
                # add the deps: dep1.py (module) and dep2/ (package)
                touch_file(site_pkgs, 'dep1.py')
                os.makedirs(os.path.join(site_pkgs, 'dep2'))
                touch_file(os.path.join(site_pkgs, 'dep2'), '__init__.py')
                touch_file(os.path.join(site_pkgs, 'dep2'), 'foo.py')
                os.makedirs(os.path.join(site_pkgs, 'foodep3'))
                touch_file(os.path.join(site_pkgs, 'foodep3'), '__init__.py')
                touch_file(os.path.join(site_pkgs, 'foodep3'), 'foodep3.py')
                return 0

            with mock.patch('subprocess.Popen') as sppo:
                instance = sppo.return_value
                instance.wait.side_effect = tox_fetch_deps
                zpm.bundle_project(tempdir)
            # Test the deps file:
            with open(os.path.join(tempdir, '.zapp', 'deps.txt')) as deps_file:
                assert 'dep1\ndep2\ndontcare\n' == deps_file.read()
            # Test the subprocess call to tox:
            assert sppo.call_args[0][0] == [
                'tox', '-c', os.path.join(tempdir, '.zapp', 'tox.ini')
            ]
            tar = tarfile.open(zapp_file)
            expected_file_names = [
                'boot/system.map',
                'zapp.yaml',
                'main.py',
                'lib/python2.7/site-packages/dep1.py',
                'lib/python2.7/site-packages/dep2',
                'lib/python2.7/site-packages/dep2/__init__.py',
                'lib/python2.7/site-packages/dep2/foo.py',
                'lib/python2.7/site-packages/foodep3',
                'lib/python2.7/site-packages/foodep3/__init__.py',
                'lib/python2.7/site-packages/foodep3/foodep3.py',
            ]
            assert sorted(expected_file_names) == sorted(
                [x.name for x in tar.getmembers()]
            )
            tar.close()

            ###################################
            # Test bundling with --refresh-deps
            # Different dependencies this time
            zapp['dependencies'] = ['dep1']
            with open(os.path.join(tempdir, 'zapp.yaml'), 'w') as zapp_yaml:
                zapp_yaml.write(yaml.dump(zapp))

            def tox_fetch_deps(*args, **kwargs):
                # fake creating a venv and installing deps with tox
                shutil.rmtree(site_pkgs)
                os.makedirs(site_pkgs)
                # add the deps: dep1.py (module) and dep2/ (package)
                touch_file(site_pkgs, 'dep1.py')
                return 0

            with mock.patch('subprocess.Popen') as sppo:
                instance = sppo.return_value
                instance.wait.side_effect = tox_fetch_deps
                zpm.bundle_project(tempdir, refresh_deps=True)

            assert sppo.call_args[0][0] == [
                'tox', '-r', '-c', os.path.join(tempdir, '.zapp', 'tox.ini')
            ]

            tar = tarfile.open(zapp_file)
            expected_file_names = [
                'boot/system.map',
                'zapp.yaml',
                'main.py',
                'lib/python2.7/site-packages/dep1.py',
            ]
            assert sorted(expected_file_names) == sorted(
                [x.name for x in tar.getmembers()]
            )
            tar.close()
        finally:
            shutil.rmtree(tempdir)

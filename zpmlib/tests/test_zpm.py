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

import copy
import json
import mock
import os
import pytest
import shutil
import tarfile
import tempfile
import yaml
import zpmlib
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from zpmlib import zpm


class TestCreateProject:
    """
    Tests for :func:`zpmlib.zpm.create_project`.
    """

    def test_path_exists_not_dir(self):
        # A RuntimeError should be thrown if the target path exists and is
        # not a dir.
        _, tf = tempfile.mkstemp()
        with mock.patch('zpmlib.zpm._create_zapp_yaml') as czy:
            with pytest.raises(RuntimeError):
                zpm.create_project(tf)
            assert czy.call_count == 0

    def test_path_does_not_exist(self):
        # If the path does not exist, `create_project` should create the
        # directory (including intermediate directories) and bootstrap an empty
        # project.
        tempdir = tempfile.mkdtemp()
        target_dir = os.path.join(tempdir, 'foo', 'bar')

        try:
            with mock.patch('zpmlib.zpm._create_zapp_yaml') as czy:
                zpm.create_project(target_dir)
                assert czy.call_count == 1
        finally:
            shutil.rmtree(tempdir)

    def test_target_is_dir(self):
        # In this case, the target is a dir and it exists already.
        tempdir = tempfile.mkdtemp()
        try:
            with mock.patch('zpmlib.zpm._create_zapp_yaml') as czy:
                zpm.create_project(tempdir)
                assert czy.call_count == 1
        finally:
            shutil.rmtree(tempdir)


class TestCreateZappYAML:
    """
    Tests for :func:`zpmlib.zpm._create_zapp_yaml`.
    """

    def test_file_already_exists(self):
        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'zapp.yaml')
        # "touch" the file
        open(filepath, 'w').close()
        try:
            with pytest.raises(RuntimeError):
                zpm._create_zapp_yaml(tempdir)
        finally:
            shutil.rmtree(tempdir)

    def test_create_zapp_yaml(self):
        # Test the creation of zapp.yaml.
        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'zapp.yaml')
        name = os.path.basename(tempdir)

        try:
            assert not os.path.exists(filepath)
            zapp_yaml = zpm._create_zapp_yaml(tempdir)
            assert os.path.exists(filepath)
            with open(filepath) as fp:
                expected = yaml.load(zpm.render_zapp_yaml(name))
                assert expected == yaml.load(fp)
            assert os.path.abspath(filepath) == os.path.abspath(zapp_yaml)
        finally:
            shutil.rmtree(tempdir)

    @mock.patch('yaml.constructor.SafeConstructor.construct_yaml_map')
    def test_key_ordering(self, yaml_map):
        # This makes yaml.safe_load use an OrderedDict instead of a
        # normal dict when loading a YAML mapping.
        yaml_map.__iter__.return_value = iter(OrderedDict())

        # Test the creation of zapp.yaml.
        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'zapp.yaml')

        try:
            zpm._create_zapp_yaml(tempdir)
            with open(filepath) as fp:
                loaded = yaml.safe_load(fp)
                tmpl = yaml.safe_load(zpm.render_zapp_yaml(''))
                assert loaded.keys() == tmpl.keys()
        finally:
            shutil.rmtree(tempdir)


class TestFindUIUploads:
    """
    Tests for :func:`zpmlib.zpm._find_ui_uploads`.
    """

    def test_without_ui(self):
        matches = zpm._find_ui_uploads({}, None)
        assert matches == zpm._DEFAULT_UI_TEMPLATES

    def test_with_ui(self):
        zapp = {'ui': ['x']}
        tar = mock.Mock(getnames=lambda: ['x', 'y'])
        matches = zpm._find_ui_uploads(zapp, tar)
        assert sorted(matches) == ['x']

    def test_with_glob(self):
        zapp = {'ui': ['x', 'ui/*']}
        tar = mock.Mock(getnames=lambda: ['x', 'y', 'ui/x', 'ui/y'])
        matches = zpm._find_ui_uploads(zapp, tar)
        assert sorted(matches) == ['ui/x', 'ui/y', 'x']


def test__prepare_job():
    # Test for `zpmlib.zpm._prepare_job`.

    # Contents of `myapp.json`, which is expected to be in the `myapp.zapp`
    # archive.
    myapp_json = [
        {'exec': {'args': 'myapp.py', 'path': 'file://python2.7:python'},
         'file_list': [{'device': 'python2.7'}, {'device': 'stdout'}],
         'name': 'myapp'}
    ]
    zapp = {'meta': {'name': 'myapp'}}
    zapp_swift_url = ('swift://AUTH_469a9cd20b5a4fc5be9438f66bb5ee04/'
                      'test_container/hello.zapp')

    # Expected result
    exp_job_json = copy.deepcopy(myapp_json)
    exp_job_json[0]['file_list'].append(
        {'device': 'image', 'path': zapp_swift_url}
    )

    tempdir = tempfile.mkdtemp()
    try:
        tempzapp = os.path.join(tempdir, 'myapp.zapp')
        tf = tarfile.open(tempzapp, 'w:gz')
        temp_myapp_json = os.path.join(tempdir, 'myapp.json')
        with open(temp_myapp_json, 'w') as fp:
            json.dump(myapp_json, fp)
        tf.add(temp_myapp_json, arcname='myapp.json')
        tf.close()

        tf = tarfile.open(tempzapp, 'r:gz')
        job = zpm._prepare_job(tf, zapp, zapp_swift_url)
        tf.close()
        assert exp_job_json == job
    finally:
        shutil.rmtree(tempdir)


class TestFindProjectRoot:
    """
    Tests for :func:`zpmlib.zpm.find_project_root`.
    """

    def setup_method(self, _method):
        self.tempdir = tempfile.mkdtemp()
        self.subdir = os.path.join(self.tempdir, 'foo', 'bar')
        os.makedirs(self.subdir)

    def test_zapp_yaml_exists(self):
        try:
            zapp_path = os.path.join(self.tempdir, 'zapp.yaml')
            # "touch" the file
            open(zapp_path, 'w').close()

            with mock.patch('os.getcwd') as cwd:
                cwd.return_value = self.subdir

                root = zpm.find_project_root()
                assert root == self.tempdir
        finally:
            shutil.rmtree(self.tempdir)

    def test_zapp_yaml_not_exists(self):
        try:
            with mock.patch('os.getcwd') as cwd:
                cwd.return_value = self.subdir

                with pytest.raises(RuntimeError):
                    zpm.find_project_root()
        finally:
            shutil.rmtree(self.tempdir)


def test__generate_job_desc():
    # Test :func:`zpmlib.zpm._generate_job_desc`.
    zapp_yaml_contents = {
        'bundling': ['mapper.py', 'reducer.py'],
        'execution': {
            'groups': [
                {'args': r'mapper.py "foo\\, \nbar"',
                 'devices': [
                     {'name': 'python2.7'},
                     {'name': 'stdout'},
                     {'name': 'input_swift_file',
                      'path': 'swift://AUTH_abc123/foo/bar.txt'},
                 ],
                 'name': 'mapper',
                 'connect': ['reducer'],
                 'path': 'file://python2.7:python'},
                {'args': 'reducer.py',
                 'devices': [
                     {'name': 'python2.7'},
                     {'name': 'stdout'},
                 ],
                 'name': 'reducer',
                 'path': 'file://python2.7:python'},
            ]
        },
        'help': {'args': [['loglevel', 'Log Level']],
                 'description': 'sample map/reduce app'},
        'meta': {'Author-email': 'John Doe <jdoe@example.com',
                 'Summary': 'Sample map/reduce app',
                 'Version': '0.1',
                 'name': 'mapreduce'}
    }

    expected_job = [
        {'file_list': [
            {'device': 'python2.7'},
            {'device': 'stdout'},
            {'device': 'input_swift_file',
             'path': 'swift://AUTH_abc123/foo/bar.txt'}],
         'connect': ['reducer'],
         'name': 'mapper',
         'exec': {'path': 'file://python2.7:python',
                  'args': 'mapper.py foo\\x5c\\x2c\\x20\\x5cnbar'}},
        {'file_list': [
            {'device': 'python2.7'},
            {'device': 'stdout'}],
         'name': 'reducer',
         'exec': {'path': 'file://python2.7:python', 'args': 'reducer.py'}},
    ]

    actual_job = zpm._generate_job_desc(zapp_yaml_contents)
    assert actual_job == expected_job


class TestGetZeroCloudConn:
    """
    Tests for :func:`zpmlib.zpm._get_zerocloud_conn`.
    """

    def setup_method(self, _method):
        self.v1_args = mock.Mock()
        self.v1_args.auth_version = '1.0'
        self.v1_args.auth = 'http://example.com/auth/v1.0'
        self.v1_args.user = 'tenant1:user1'
        self.v1_args.key = 'secret'

        self.v2_args = mock.Mock()
        self.v2_args.auth_version = '2.0'
        self.v2_args.os_auth_url = 'http://example.com/v2.0'
        self.v2_args.os_username = 'user1'
        self.v2_args.os_password = 'secret'
        self.v2_args.os_tenant_name = 'tenant1'

    def test_v1(self):
        conn = zpm._get_zerocloud_conn(self.v1_args)
        assert conn.authurl == self.v1_args.auth
        assert conn.user == self.v1_args.user
        assert conn.key == self.v1_args.key

    def test_v1_fail(self):
        self.v1_args.user = None
        with pytest.raises(zpmlib.ZPMException):
            zpm._get_zerocloud_conn(self.v1_args)

    def test_v2(self):
        conn = zpm._get_zerocloud_conn(self.v2_args)
        assert conn.authurl == self.v2_args.os_auth_url
        assert conn.user == self.v2_args.os_username
        assert conn.key == self.v2_args.os_password
        assert conn.os_options['tenant_name'] == self.v2_args.os_tenant_name

    def test_v2_fail(self):
        self.v2_args.os_tenant_name = None
        with pytest.raises(zpmlib.ZPMException):
            zpm._get_zerocloud_conn(self.v2_args)

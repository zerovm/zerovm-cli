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
import gzip
import jinja2
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
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from zpmlib import zpm, commands


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


class TestDeploy:
    """
    Tests :function:`zpmlib.zpm.deploy` and its helper functions.
    """

    @classmethod
    def setup_class(cls):
        cls.zapp_yaml_contents = """\
execution:
  groups:
    - name: "hello"
      path: file://python2.7:python
      args: "hello.py"
      devices:
      - name: python
      - name: stdout
meta:
  Version: ""
  name: "hello"
  Author-email: ""
  Summary: ""
help:
  description: ""
  args:
  - ["", ""]
bundling:
  - "hello.py"
ui:
  - "index.html"
""".encode('utf-8')

        cls.job_json_contents = json.dumps([
            {'exec': {'args': 'hello.py', 'path': 'file://python2.7:python'},
             'file_list': [{'device': 'python'}, {'device': 'stdout'}],
             'name': 'hello'}
        ]).encode('utf-8')
        cls.job_json_prepped = json.dumps([
            {"exec": {"path": "file://python2.7:python", "args": "hello.py"},
             "file_list": [{"device": "python"}, {"device": "stdout"},
                           {"device": "image",
                            "path": "swift:///container1/foo/bar/zapp.yaml"}],
             "name": "hello"}
        ]).encode('utf-8')

        cls.hellopy_contents = b"""\
print("Hello from ZeroVM!")
"""

        cls.indexhtml_contents = bytearray("""\
<html>
<head><title>Hello!</title></head>
<body>Hello from ZeroVM!</body>
</html>""", 'utf-8')

        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_zapp_file = '%s/zapp.yaml' % cls.temp_dir
        tar = tarfile.open(cls.temp_zapp_file, 'w:gz')

        info = tarfile.TarInfo(name='hello.json')
        info.size = len(cls.job_json_contents)
        tar.addfile(info, BytesIO(cls.job_json_contents))

        info = tarfile.TarInfo(name='zapp.yaml')
        info.size = len(cls.zapp_yaml_contents)
        tar.addfile(info, BytesIO(cls.zapp_yaml_contents))

        info = tarfile.TarInfo(name='hello.py')
        info.size = len(cls.hellopy_contents)
        tar.addfile(info, BytesIO(cls.hellopy_contents))

        info = tarfile.TarInfo(name='index.html')
        info.size = len(cls.indexhtml_contents)
        tar.addfile(info, BytesIO(cls.indexhtml_contents))
        tar.close()

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.temp_dir)

    def setup_method(self, _method):
        self.conn = mock.Mock()
        self.target = 'container1/foo/bar'
        self.zapp_path = self.temp_zapp_file

        self.conn.url = 'http://example.com'
        args = mock.Mock()
        args.auth = 'http://example.com/auth/v1.0'
        args.user = 'user1'
        args.key = 'secret'
        self.auth_opts = jinja2.Markup(
            json.dumps(zpm._prepare_auth('1.0', args, self.conn))
        )

    def test__prepare_uploads(self):
        uploads = zpm._prepare_uploads(self.conn, self.target,
                                       self.zapp_path, self.auth_opts)

        expected_uploads = [
            ('%s/zapp.yaml' % self.target, gzip.open(self.zapp_path).read()),
            ('%s/hello.json' % self.target,
             self.job_json_prepped.decode('utf-8')),
            ('%s/index.html' % self.target,
             self.indexhtml_contents.decode('utf-8')),
        ]
        assert uploads[0] == expected_uploads[0]
        assert uploads[1][0] == expected_uploads[1][0]
        assert json.loads(uploads[1][1]) == json.loads(expected_uploads[1][1])
        assert uploads[2] == expected_uploads[2]

    def test__deploy_zapp(self):
        with mock.patch('zpmlib.zpm._prepare_uploads') as pu:
            pu.return_value = [('x/a', 'b'), ('x/c', 'd')]
            zpm._deploy_zapp(self.conn, self.target, self.zapp_path,
                             self.auth_opts)

            put_object = self.conn.put_object
            assert put_object.call_count == 2
            assert put_object.call_args_list == [mock.call('x', 'a', 'b'),
                                                 mock.call('x', 'c', 'd')]

    def test_deploy_project_execute(self):
        parser = commands.set_up_arg_parser()
        args = parser.parse_args(['deploy', 'foo', self.zapp_path, '--exec'])

        job_path = '%s.json' % os.path.splitext(self.zapp_path)[0]
        job_json = self.job_json_contents.decode('utf-8')
        job = json.loads(job_json)

        with mock.patch('zpmlib.zpm._get_zerocloud_conn') as gzc:
            gzc.return_value = self.conn
            get_object = self.conn.get_object
            get_object.return_value = ([], job_json)
            post_job = self.conn.post_job
            zpm.deploy_project(args)
            assert get_object.call_args_list == [mock.call('foo', job_path)]
            assert post_job.call_args_list == [mock.call(job)]


def test__prepare_auth_v0():
    # Test for :func:`zpmlib.zpm._prepare_auth`, with version 0.0
    version = '0.0'
    args = None
    conn = mock.Mock()
    conn.url = 'http://example.com'

    expected = {
        'version': '0.0',
        'swiftUrl': 'http://example.com',
    }
    assert zpm._prepare_auth(version, args, conn) == expected


def test__prepare_auth_v1():
    # Test for :func:`zpmlib.zpm._prepare_auth`, with version 1.0
    version = '1.0'
    args = mock.Mock()
    args.auth = 'http://example.com/auth/v1.0'
    args.user = 'user1'
    args.key = 'secret'
    conn = None

    expected = {
        'version': '1.0',
        'authUrl': 'http://example.com/auth/v1.0',
        'username': 'user1',
        'password': 'secret',
    }
    assert zpm._prepare_auth(version, args, conn) == expected


def test__prepare_auth_v2():
    # Test for :func:`zpmlib.zpm._prepare_auth`, with version 2.0
    version = '2.0'
    args = mock.Mock()
    args.os_auth_url = 'http://example.com:5000/v2.0'
    args.os_username = 'user1'
    args.os_tenant_name = 'tenant1'
    args.os_password = 'secret'
    conn = None

    expected = {
        'version': '2.0',
        'authUrl': 'http://example.com:5000/v2.0',
        'tenant': 'tenant1',
        'username': 'user1',
        'password': 'secret',
    }
    assert zpm._prepare_auth(version, args, conn) == expected

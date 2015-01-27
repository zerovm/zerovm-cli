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
import swiftclient.exceptions
import tarfile
import tempfile
import zpmlib
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from zpmlib import zpm, commands


class TestFindUIUploads:
    """
    Tests for :func:`zpmlib.zpm._find_ui_uploads`.
    """

    def test_with_files(self):
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

    # Contents of `boot/system.map`, which is expected to be in the
    # `myapp.zapp` archive.
    myapp_json = [
        {'exec': {'args': 'myapp.py', 'path': 'file://python2.7:python'},
         'devices': [{'name': 'python2.7'}, {'name': 'stdout'}],
         'name': 'myapp'}
    ]
    zapp = {'meta': {'name': 'myapp'}}
    zapp_swift_url = ('swift://AUTH_469a9cd20b5a4fc5be9438f66bb5ee04/'
                      'test_container/hello.zapp')

    # Expected result
    exp_job_json = copy.deepcopy(myapp_json)
    exp_job_json[0]['devices'].append(
        {'name': 'image', 'path': zapp_swift_url}
    )

    tempdir = tempfile.mkdtemp()
    try:
        tempzapp = os.path.join(tempdir, 'myapp.zapp')
        tf = tarfile.open(tempzapp, 'w:gz')

        # prepare a sample job description
        system_map = os.path.join(tempdir, 'system.map')
        with open(system_map, 'w') as fp:
            json.dump(myapp_json, fp)

        tf.add(system_map, arcname='boot/system.map')
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
                 'env': {'FOO': 'bar', 'BAZ': 5},
                 'path': 'swift://./container/python'},
                {'args': r'mapper.py "foo\\, \nbar"',
                 'devices': [
                     {'name': 'python2.7'},
                     {'name': 'stdout'},
                     {'name': 'input_swift_file',
                      'path': 'swift://AUTH_abc123/foo/bar.txt'},
                 ],
                 'name': 'mapper',
                 'connect': ['reducer'],
                 'env': {'FOO': 'bar', 'BAZ': 5},
                 'path': 'swift://~/container/path/to/python'},

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
        {'devices': [
            {'name': 'python2.7'},
            {'name': 'stdout'},
            {'name': 'input_swift_file',
             'path': 'swift://AUTH_abc123/foo/bar.txt'}],
         'connect': ['reducer'],
         'name': 'mapper',
         'exec': {'path': 'swift://./container/python',
                  'name': 'python',
                  'args': 'mapper.py foo\\x5c\\x2c\\x20\\x5cnbar',
                  'env': {'FOO': 'bar', 'BAZ': 5}}},
        {'devices': [
            {'name': 'python2.7'},
            {'name': 'stdout'},
            {'name': 'input_swift_file',
             'path': 'swift://AUTH_abc123/foo/bar.txt'}],
         'connect': ['reducer'],
         'name': 'mapper',
         'exec': {'path': 'swift://~/container/path/to/python',
                  'name': 'path/to/python',
                  'args': 'mapper.py foo\\x5c\\x2c\\x20\\x5cnbar',
                  'env': {'FOO': 'bar', 'BAZ': 5}}},
        {'devices': [
            {'name': 'python2.7'},
            {'name': 'stdout'}],
         'name': 'reducer',
         'exec': {'path': 'file://python2.7:python',
                  'name': 'python',
                  'args': 'reducer.py'}},
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

    def test_no_auth_details_given(self):
        args = mock.Mock()
        args.auth_version = None
        args.auth = None
        args.user = None
        args.key = None
        args.os_auth_url = None
        args.os_username = None
        args.os_password = None
        args.os_tenant_name = None

        env = dict.fromkeys([
            'ST_AUTH', 'ST_USER', 'ST_KEY',
            'OS_AUTH_URL', 'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME',
        ], '')
        with mock.patch.dict('os.environ', env):
            with pytest.raises(zpmlib.ZPMException):
                zpm._get_zerocloud_conn(args)


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
  - "foo.js.tmpl"
""".encode('utf-8')

        cls.job_json_contents = json.dumps([
            {'exec': {'args': 'hello.py', 'path': 'file://python2.7:python'},
             'devices': [{'name': 'python'}, {'name': 'stdout'}],
             'name': 'hello'}
        ]).encode('utf-8')
        cls.job_json_prepped = json.dumps([
            {"exec": {"path": "file://python2.7:python", "args": "hello.py"},
             "devices": [{"name": "python"}, {"name": "stdout"},
                         {"name": "image",
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

        cls.foojstmpl_contents = b"var opts = {{ auth_opts }};"

        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_zapp_file = '%s/zapp.yaml' % cls.temp_dir
        tar = tarfile.open(cls.temp_zapp_file, 'w:gz')

        info = tarfile.TarInfo(name='foo.js.tmpl')
        info.size = len(cls.foojstmpl_contents)
        tar.addfile(info, BytesIO(cls.foojstmpl_contents))

        info = tarfile.TarInfo(name='boot/system.map')
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
        self.conn.get_container.return_value = (
            {},  # response headers
            [],  # object list
        )

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

    def test__generate_uploads(self):
        uploads = zpm._generate_uploads(self.conn, self.target,
                                        self.zapp_path, self.auth_opts)
        uploads = list(uploads)

        foojs_tmpl = jinja2.Template(self.foojstmpl_contents.decode())
        foojs = foojs_tmpl.render(auth_opts=self.auth_opts)

        expected_uploads = [
            ('%s/zapp.yaml' % self.target, gzip.open(self.zapp_path).read(),
             'application/x-tar'),
            ('%s/boot/system.map' % self.target,
             self.job_json_prepped.decode('utf-8'),
             'application/json'),
            ('%s/foo.js' % self.target, foojs, None),
            ('%s/index.html' % self.target, self.indexhtml_contents, None),
        ]
        assert uploads[0] == expected_uploads[0]
        assert uploads[1][0] == expected_uploads[1][0]
        assert json.loads(uploads[1][1]) == json.loads(expected_uploads[1][1])
        assert uploads[2] == expected_uploads[2]
        assert uploads[3] == expected_uploads[3]

    def test__deploy_zapp(self):
        with mock.patch('zpmlib.zpm._generate_uploads') as gu:
            gu.return_value = iter([('x/a', 'b', None), ('x/c', 'd', None)])
            zpm._deploy_zapp(self.conn, self.target, self.zapp_path,
                             self.auth_opts)

            put_object = self.conn.put_object
            assert put_object.call_count == 2
            assert put_object.call_args_list == [
                mock.call('x', 'a', 'b', content_type=None),
                mock.call('x', 'c', 'd', content_type=None)]

    def test__deploy_zapp_with_index_html(self):
        with mock.patch('zpmlib.zpm._generate_uploads') as gu:
            gu.return_value = iter([('cont/dir/index.html', 'data',
                                     'text/html')])
            index = zpm._deploy_zapp(self.conn, 'cont', None, None)
            assert index == 'cont/dir/index.html'

            put_object = self.conn.put_object
            assert put_object.call_count == 1
            assert put_object.call_args_list == [
                mock.call('cont', 'dir/index.html', 'data',
                          content_type='text/html')
            ]

    def test__deploy_zapp_without_index_html(self):
        with mock.patch('zpmlib.zpm._generate_uploads') as gu:
            gu.return_value = iter([('cont/foo.html', 'data', 'text/html')])
            index = zpm._deploy_zapp(self.conn, 'cont', None, None)
            assert index == 'cont/'

            put_object = self.conn.put_object
            assert put_object.call_count == 1
            assert put_object.call_args_list == [
                mock.call('cont', 'foo.html', 'data',
                          content_type='text/html')
            ]

    def test__deploy_zapp_container_not_empty(self):
        self.conn.get_container.return_value = (
            {},  # response headers
            # The actual files list response from Swift is a list of
            # dictionaries. For these tests, we don't actually check the
            # content; just length of the file list.
            ['file1'],
        )

        with pytest.raises(zpmlib.ZPMException) as exc:
            zpm._deploy_zapp(self.conn, 'target/dir1/dir2', None, None)

        assert str(exc.value) == (
            "Target container ('target') is not empty.\n"
            "Deploying to a non-empty container can cause consistency "
            "problems with overwritten objects.\n"
            "Specify the flag `--force/-f` to overwrite anyway."
        )
        assert self.conn.get_container.call_args_list == [mock.call('target')]

    def test__deploy_zapp_container_not_empty_force(self):
        self.conn.get_container.return_value = ({}, ['file1'])

        with mock.patch('zpmlib.zpm._generate_uploads') as gu:
            gu.return_value = iter([('x/a', 'b', None), ('x/c', 'd', None)])
            zpm._deploy_zapp(self.conn, self.target, self.zapp_path,
                             self.auth_opts, force=True)

            put_object = self.conn.put_object
            assert put_object.call_count == 2
            assert put_object.call_args_list == [
                mock.call('x', 'a', 'b', content_type=None),
                mock.call('x', 'c', 'd', content_type=None)]

    def test__deploy_zapp_container_doesnt_exist(self):
        self.conn.get_container.side_effect = (
            swiftclient.exceptions.ClientException(None)
        )

        with mock.patch('zpmlib.zpm._generate_uploads') as gu:
            gu.return_value = iter([('target/dir/foo.py', 'data', None)])
            zpm._deploy_zapp(self.conn, 'target/dir', None, None)

            # check that the container is created
            assert self.conn.put_container.call_count == 1
            assert self.conn.put_container.call_args_list == [
                mock.call('target')
            ]
            # check that files are uploaded correctly
            assert self.conn.put_object.call_count == 1
            assert self.conn.put_object.call_args_list == [
                mock.call('target', 'dir/foo.py', 'data', content_type=None)
            ]

    def test_deploy_project_execute(self):
        job_path = 'boot/system.map'
        job_json = self.job_json_contents.decode('utf-8')
        job_dict = json.loads(job_json)

        class FakeZeroCloudConnection(mock.Mock):
            url = 'http://127.0.0.1'
            token = 'abc123'

            def post_job(self, job, response_dict=None,
                         response_body_buffer=None):
                response_dict['status'] = 200
                response_dict['reason'] = 'OK'
                response_dict['headers'] = {
                    'x-nexe-system': 'node-1',
                    'x-nexe-cdr-line': (
                        '5.121, 4.993, 0.13 3.84 1025 75943662 23 735 8 399 0 '
                        '0'
                    ),
                    'x-nexe-status': 'ok',
                    'x-nexe-retcode': '0',
                }
                # Check the job is passed properly here
                assert job == job_dict

            def get_container(self, *args, **kwargs):
                return {}, []

        self.conn = FakeZeroCloudConnection()
        self.conn.auth_version = '1.0'

        parser = commands.set_up_arg_parser()
        args = parser.parse_args(['deploy', 'foo', self.zapp_path, '--exec'])

        with mock.patch('zpmlib.zpm._get_zerocloud_conn') as gzc:
            gzc.return_value = self.conn
            self.conn.get_object = mock.Mock()
            get_object = self.conn.get_object
            get_object.return_value = ([], job_json)
            zpm.deploy_project(args)
            assert get_object.call_args_list == [mock.call('foo', job_path)]


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
    # Make sure that we're robust enough to handle slightly varied version
    # inputs.
    version = '1'
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
    # Make sure that we're robust enough to handle slightly varied version
    # inputs.
    version = '2'
    assert zpm._prepare_auth(version, args, conn) == expected


class TestGuessAuthVersion:

    def setup_method(self, _method):
        self.args = mock.Mock()
        self.args.auth = None
        self.args.user = None
        self.args.key = None
        self.args.os_auth_url = None
        self.args.os_username = None
        self.args.os_password = None
        self.args.os_tenant_name = None

    def test_args_v1(self):
        args = self.args
        args.auth = 'auth'
        args.user = 'user'
        args.key = 'key'
        args.os_auth_url = 'authurl'
        assert zpm._guess_auth_version(args) == '1.0'

    def test_args_v2(self):
        args = self.args
        args.os_auth_url = 'authurl'
        args.os_username = 'username'
        args.os_password = 'password'
        args.os_tenant_name = 'tenant'
        args.auth = 'auth'
        assert zpm._guess_auth_version(args) == '2.0'

    def test_args_default(self):
        args = self.args
        args.auth = 'auth'
        args.user = 'user'
        args.key = 'key'
        args.os_auth_url = 'authurl'
        args.os_username = 'username'
        args.os_password = 'password'
        args.os_tenant_name = 'tenant'
        assert zpm._guess_auth_version(args) == '1.0'

    def test_env_v1(self):
        env = dict(
            ST_AUTH='auth',
            ST_USER='user',
            ST_KEY='key',
            OS_AUTH_URL='',
            OS_USERNAME='username',
            OS_PASSWORD='',
            OS_TENANT_NAME='',
        )
        with mock.patch.dict('os.environ', env):
            assert zpm._guess_auth_version(self.args) == '1.0'

    def test_env_v2(self):
        env = dict(
            ST_AUTH='',
            ST_USER='user',
            ST_KEY='',
            OS_AUTH_URL='authurl',
            OS_USERNAME='username',
            OS_PASSWORD='password',
            OS_TENANT_NAME='tenant',
        )
        with mock.patch.dict('os.environ', env):
            assert zpm._guess_auth_version(self.args) == '2.0'

    def test_env_default(self):
        env = dict(
            ST_AUTH='auth',
            ST_USER='user',
            ST_KEY='key',
            OS_AUTH_URL='authurl',
            OS_USERNAME='username',
            OS_PASSWORD='password',
            OS_TENANT_NAME='tenant',
        )
        with mock.patch.dict('os.environ', env):
            assert zpm._guess_auth_version(self.args) == '1.0'

    def test_none(self):
        env = dict.fromkeys([
            'ST_AUTH', 'ST_USER', 'ST_KEY',
            'OS_AUTH_URL', 'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME',
        ], '')
        with mock.patch.dict('os.environ', env):
            assert zpm._guess_auth_version(self.args) is None


class TestExecSummaryTable:

    def test__get_exec_table_data_1_row(self):
        headers = {
            'content-length': '20',
            'content-type': 'text/html',
            'date': 'Tue, 26 Aug 2014 09:27:08 GMT',
            'etag': 'af0983cb8fef30642bae9ba0010e7a77',
            'x-chain-total-time': '3.920',
            'x-nexe-cdr-line': (
                '3.920, 3.913, 0.11 3.37 1025 75943644 2 20 0 0 0 0'
            ),
            'x-nexe-etag': 'disabled',
            'x-nexe-policy': 'Policy-0',
            'x-nexe-retcode': '0',
            'x-nexe-status': 'ok',
            'x-nexe-system': 'hello',
            'x-nexe-validation': '0',
            'x-timestamp': '1409045228.85265',
            'x-trans-id': 'tx1d61239ed02a56fbbfe5d-0053fc52e9',
            'x-zerovm-device': 'stdout',
        }

        expected_total_t = '3.920'
        expected_table = [
            ['hello', 'ok', '0', '3.913', '0.11', '3.37', '1025', '75943644',
             '2', '20', '0', '0', '0', '0']
        ]
        actual_total_t, actual_table = zpm._get_exec_table_data(headers)
        assert actual_total_t == expected_total_t
        assert actual_table == expected_table

    def test__get_exec_table_data_many_rows(self):
        cdr_line = (
            '5.121, '
            '4.993, 0.13 3.84 1025 75943662 23 735 8 399 0 0,'
            '4.511, 0.12 4.00 1026 75943758 0 0 0 0 1 11,'
            '4.468, 0.10 3.96 1026 75943758 0 0 0 0 1 11,'
            '4.965, 0.18 4.20 1025 75943664 0 0 15 33 5 100,'
            '4.962, 0.13 3.94 1025 75943664 0 0 15 33 5 100'
        )

        headers = {
            'content-length': '0',
            'content-type': 'application/x-gtar',
            'date': 'Tue, 26 Aug 2014 09:29:44 GMT',
            'etag': '753e7eac4298c4994a7a19c7c783bad5',
            'x-chain-total-time': '5.121',
            'x-nexe-cdr-line': cdr_line,
            'x-nexe-etag': 'disabled,disabled,disabled,disabled,disabled',
            'x-nexe-policy': 'Policy-0,Policy-0,Policy-0,Policy-0,Policy-0',
            'x-nexe-retcode': '1,0,0,0,0',
            'x-nexe-status': 'some error,ok,ok,ok,ok',
            'x-nexe-system': 'combiner,mapper-1,mapper-2,reducer-1,reducer-2',
            'x-nexe-validation': '1,0,0,0,0',
            'x-timestamp': '1409045384.22744',
            'x-trans-id': 'txa881f777891648f4834d6-0053fc5382',
        }

        expected_total_t = '5.121'
        expected_table = [
            ['combiner', 'some error', '1', '4.993', '0.13', '3.84', '1025',
             '75943662', '23', '735', '8', '399', '0', '0'],
            ['mapper-1', 'ok', '0', '4.511', '0.12', '4.00', '1026',
             '75943758', '0', '0', '0', '0', '1', '11'],
            ['mapper-2', 'ok', '0', '4.468', '0.10', '3.96', '1026',
             '75943758', '0', '0', '0', '0', '1', '11'],
            ['reducer-1', 'ok', '0', '4.965', '0.18', '4.20', '1025',
             '75943664', '0', '0', '15', '33', '5', '100'],
            ['reducer-2', 'ok', '0', '4.962', '0.13', '3.94', '1025',
             '75943664', '0', '0', '15', '33', '5', '100'],
        ]
        actual_total_t, actual_table = zpm._get_exec_table_data(headers)
        assert actual_total_t == expected_total_t
        assert actual_table == expected_table

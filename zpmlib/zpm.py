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

import fnmatch
import glob
import gzip
import jinja2
import json
import os
import shlex
import tarfile
import yaml
import zpmlib
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import swiftclient


_DEFAULT_UI_TEMPLATES = ['index.html', 'style.css', 'zerocloud.js']

LOG = zpmlib.get_logger(__name__)


def create_project(location):
    """
    Create a ZeroVM application project by writing a default `zapp.yaml` in the
    specified directory `location`.

    :returns: Full path to the created `zapp.yaml` file.
    """
    if os.path.exists(location):
        if not os.path.isdir(location):
            # target must be an empty directory
            raise RuntimeError("Target `location` must be a directory")
    else:
        os.makedirs(location)
    return _create_zapp_yaml(location)


def render_zapp_yaml(name):
    """Load and render the zapp.yaml template."""
    loader = jinja2.PackageLoader('zpmlib', 'templates')
    env = jinja2.Environment(loader=loader)
    tmpl = env.get_template('zapp.yaml')
    return tmpl.render(name=name)


def _create_zapp_yaml(location):
    """
    Create a default `zapp.yaml` file in the specified directory `location`.

    Raises a `RuntimeError` if the `location` already contains a `zapp.yaml`
    file.
    """
    filepath = os.path.join(location, 'zapp.yaml')
    if os.path.exists(filepath):
        raise RuntimeError("'%s' already exists!" % filepath)

    with open(os.path.join(location, 'zapp.yaml'), 'w') as fp:
        name = os.path.basename(os.path.abspath(location))
        fp.write(render_zapp_yaml(name))

    return filepath


def find_project_root():
    """
    Starting from the `cwd`, search up the file system hierarchy until a
    ``zapp.yaml`` file is found. Once the file is found, return the directory
    containing it. If no file is found, raise a `RuntimeError`.
    """
    root = os.getcwd()
    while not os.path.isfile(os.path.join(root, 'zapp.yaml')):
        oldroot, root = root, os.path.dirname(root)
        if root == oldroot:
            raise RuntimeError("no zapp.yaml file found")
    return root


def _generate_job_desc(zapp):
    """
    Generate the <appname>.json file contents from the zapp config file.

    :param zapp:
        `dict` of the contents of a ``zapp.yaml`` file.
    :returns:
        `dict` of the job description
    """
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
        # On Python 2, the yaml module loads non-ASCII strings as
        # unicode objects. In Python 2.7.2 and earlier, we must give
        # shlex.split a str -- but it is an error to give shlex.split
        # a bytes object in Python 3.
        need_decode = not isinstance(cmdline, str)
        if need_decode:
            cmdline = cmdline.encode('utf8')
        args = shlex.split(cmdline)
        if need_decode:
            args = [arg.decode('utf8') for arg in args]
        return ' '.join(escape(arg) for arg in args)

    for zgroup in zapp['execution']['groups']:
        jgroup = {'name': zgroup['name']}
        jgroup['exec'] = {
            'path': zgroup['path'],
            'args': translate_args(zgroup['args']),
        }

        jgroup['file_list'] = make_file_list(zgroup)

        if 'connect' in zgroup:
            jgroup['connect'] = zgroup['connect']

        job.append(jgroup)
    return job


def _add_ui(tar, zapp):
    loader = jinja2.PackageLoader('zpmlib', 'templates')
    env = jinja2.Environment(loader=loader)

    for path in _DEFAULT_UI_TEMPLATES:
        tmpl = env.get_template(path)
        output = tmpl.render(zapp=zapp)
        # NOTE(larsbutler): Python 2.7.2 has a bug related to unicode and
        # cStringIO. To work around this, we need the following explicit
        # encoding. See http://bugs.python.org/issue1548891.
        output = output.encode('utf-8')
        info = tarfile.TarInfo(name=path)
        info.size = len(output)
        LOG.info('adding %s' % path)
        tar.addfile(info, BytesIO(output))


def _get_swift_zapp_url(swift_service_url, zapp_path):
    """
    :param str swift_service_url:
        The Swift service URL returned from a Keystone service catalog.
        Example: http://localhost:8080/v1/AUTH_469a9cd20b5a4fc5be9438f66bb5ee04

    :param str zapp_path:
        <container>/<zapp-file-name>. Example:

            test_container/myapp.zapp

    Here's a typical usage example, with typical input and output:

    >>> swift_service_url = ('http://localhost:8080/v1/'
    ...                      'AUTH_469a9cd20b5a4fc5be9438f66bb5ee04')
    >>> zapp_path = 'test_container/myapp.zapp'
    >>> _get_swift_zapp_url(swift_service_url, zapp_path)
    'swift://AUTH_469a9cd20b5a4fc5be9438f66bb5ee04/test_container/myapp.zapp'
    """
    swift_path = urlparse.urlparse(swift_service_url).path
    # TODO(larsbutler): Why do we need to check if the path contains '/v1/'?
    # This is here due to legacy reasons, but it's not clear to me why this is
    # needed.
    if swift_path.startswith('/v1/'):
        swift_path = swift_path[4:]
    return 'swift://%s/%s' % (swift_path, zapp_path)


def _prepare_job(tar, zapp, zapp_swift_url):
    """
    :param tar:
        The application .zapp file, as a :class:`tarfile.TarFile` object.
    :param dict zapp:
        Parsed contents of the application `zapp.yaml` specification, as a
        `dict`.
    :param str zapp_swift_url:
        Path of the .zapp in Swift, which looks like this::

            'swift://AUTH_abcdef123/test_container/hello.zapp'

        See :func:`_get_swift_zapp_url`.

    :returns:
        Extracted contents of the app json (example: hello.json) with the swift
        path to the .zapp added to the `file_list` for each `group`.

        So if the job looks like this::

            [{'exec': {'args': 'hello.py', 'path': 'file://python2.7:python'},
              'file_list': [{'device': 'python2.7'}, {'device': 'stdout'}],
              'name': 'hello'}]

        the output will look like something like this::

            [{'exec': {u'args': 'hello.py', 'path': 'file://python2.7:python'},
              'file_list': [
                {'device': 'python2.7'},
                {'device': 'stdout'},
                {'device': 'image',
                 'path': 'swift://AUTH_abcdef123/test_container/hello.zapp'},
              ],
              'name': 'hello'}]


    """
    fp = tar.extractfile('%s.json' % zapp['meta']['name'])
    # NOTE(larsbutler): the `decode` is needed for python3
    # compatibility
    job = json.loads(fp.read().decode('utf-8'))
    device = {'device': 'image', 'path': zapp_swift_url}
    for group in job:
        group['file_list'].append(device)

    return job


def bundle_project(root):
    """
    Bundle the project under root.
    """
    zapp_yaml = os.path.join(root, 'zapp.yaml')
    zapp = yaml.safe_load(open(zapp_yaml))

    zapp_name = zapp['meta']['name'] + '.zapp'

    tar = tarfile.open(zapp_name, 'w:gz')

    job = _generate_job_desc(zapp)
    job_json = json.dumps(job)
    info = tarfile.TarInfo(name='%s.json' % zapp['meta']['name'])
    # This size is only correct because json.dumps uses
    # ensure_ascii=True by default and we thus have a 1-1
    # correspondence between Unicode characters and bytes.
    info.size = len(job_json)

    LOG.info('adding %s' % info.name)
    # In Python 3, we cannot use a str or bytes object with addfile,
    # we need a BytesIO object. In Python 2, BytesIO is just StringIO.
    # Since json.dumps produces an ASCII-only Unicode string in Python
    # 3, it is safe to encode it to ASCII.
    tar.addfile(info, BytesIO(job_json.encode('ascii')))
    _add_file_to_tar(root, 'zapp.yaml', tar)

    sections = ('bundling', 'ui')
    # Keep track of the files we add, given the configuration in the zapp.yaml.
    file_add_count = 0
    for section in sections:
        for pattern in zapp.get(section, []):
            paths = glob.glob(os.path.join(root, pattern))
            if len(paths) == 0:
                LOG.warning(
                    "pattern '%(pat)s' in section '%(sec)s' matched no files",
                    dict(pat=pattern, sec=section)
                )
            else:
                for path in paths:
                    _add_file_to_tar(root, path, tar)
                file_add_count += len(paths)

    if file_add_count == 0:
        # None of the files specified in the "bundling" or "ui" sections were
        # found. Something is wrong.
        raise zpmlib.ZPMException(
            "None of the files specified in the 'bundling' or 'ui' sections of"
            " the zapp.yaml matched anything."
        )

    if not zapp.get('ui'):
        _add_ui(tar, zapp)

    tar.close()
    print('created %s' % zapp_name)


def _add_file_to_tar(root, path, tar):
    """
    :param root:
        Root working directory.
    :param path:
        File path.
    :param tar:
        Open :class:`tarfile.TarFile` object to add the ``files`` to.
    """
    LOG.info('adding %s' % path)
    relpath = os.path.relpath(path, root)
    info = tarfile.TarInfo(name=relpath)
    info.size = os.path.getsize(path)
    tar.addfile(info, open(path, 'rb'))


def _find_ui_uploads(zapp, tar):
    if 'ui' not in zapp:
        return _DEFAULT_UI_TEMPLATES

    matches = set()
    names = tar.getnames()
    for pattern in zapp['ui']:
        matches.update(fnmatch.filter(names, pattern))
    return sorted(matches)


def _post_job(url, token, json_data, http_conn=None, response_dict=None):
    # Modelled after swiftclient.client.post_account.
    headers = {'X-Auth-Token': token,
               'Accept': 'application/json',
               'X-Zerovm-Execute': '1.0',
               'Content-Type': 'application/json'}

    if http_conn:
        parsed, conn = http_conn
    else:
        parsed, conn = swiftclient.http_connection(url)

    conn.request('POST', parsed.path, json_data, headers)
    resp = conn.getresponse()
    body = resp.read()
    swiftclient.http_log((url, 'POST'), {'headers': headers}, resp, body)
    swiftclient.store_response(resp, response_dict)

    LOG.debug('response status: %s' % resp.status)
    print(body)


class ZeroCloudConnection(swiftclient.Connection):

    def authenticate(self):
        """
        Authenticate with the provided credentials and cache the storage URL
        and auth token as `self.url` and `self.token`, respectively.
        """
        self.url, self.token = self.get_auth()

    def post_job(self, job, response_dict=None):
        """Start a ZeroVM job, using a pre-uploaded zapp

        :param object job:
            Job description. This will be encoded as JSON and sent to
            ZeroCloud.
        """
        json_data = json.dumps(job)
        return self._retry(None, _post_job, json_data,
                           response_dict=response_dict)


def _get_zerocloud_conn(args):
    version = args.auth_version
    if version == '1.0':
        if any([arg is None for arg in (args.auth, args.user, args.key)]):
            raise zpmlib.ZPMException(
                "Version 1 auth requires `--auth`, `--user`, and `--key`."
                "\nSee `zpm deploy --help` for more information."
            )

        conn = ZeroCloudConnection(args.auth, args.user, args.key)
    else:
        if any([arg is None for arg in
                (args.os_auth_url, args.os_username, args.os_tenant_name,
                 args.os_password)]):
            raise zpmlib.ZPMException(
                "Version 2 auth requires `--os-auth-url`, `--os-username`, "
                "`--os-password`, and `--os-tenant-name`."
                "\nSee `zpm deploy --help` for more information."
            )

        conn = ZeroCloudConnection(args.os_auth_url, args.os_username,
                                   args.os_password,
                                   tenant_name=args.os_tenant_name,
                                   auth_version='2.0')

    return conn


def _deploy_zapp(conn, target, zapp_path, auth_opts):
    """
    Upload all of the necessary files for a zapp.
    """
    uploads = _generate_uploads(conn, target, zapp_path, auth_opts)
    for path, data in uploads:
        container, obj = path.split('/', 1)
        conn.put_object(container, obj, data)


def _generate_uploads(conn, target, zapp_path, auth_opts):
    """Generate sequence of (container-and-file-path, data) tuples."""
    # returns a list of pairs: (container-and-file-path, data)
    tar = tarfile.open(zapp_path, 'r:gz')
    zapp_config = yaml.safe_load(tar.extractfile('zapp.yaml'))

    remote_zapp_path = '%s/%s' % (target, os.path.basename(zapp_path))
    swift_url = _get_swift_zapp_url(conn.url, remote_zapp_path)
    job = _prepare_job(tar, zapp_config, swift_url)
    job_json_path = '%s/%s.json' % (target, zapp_config['meta']['name'])

    yield (remote_zapp_path, gzip.open(zapp_path).read())
    yield (job_json_path, json.dumps(job))

    for path in _find_ui_uploads(zapp_config, tar):
        output = tar.extractfile(path).read()
        if path.endswith('.tmpl'):
            tmpl = jinja2.Template(output.decode('utf-8'))
            output = tmpl.render(auth_opts=auth_opts)
            path = path[:-5]

        ui_path = '%s/%s' % (target, path)
        yield (ui_path, output)


def _prepare_auth(version, args, conn):
    """
    :param str version:
        Auth version: "0.0", "1.0", or "2.0". "0.0" indicates "no auth".
    :param args:
        :class:`argparse.Namespace` instance, with attributes representing the
        various authentication parameters
    :param conn:
        :class:`ZeroCloudConnection` instance.
    """
    auth = {'version': version}
    if version == '0.0':
        auth['swiftUrl'] = conn.url
    elif version == '1.0':
        auth['authUrl'] = args.auth
        auth['username'] = args.user
        auth['password'] = args.key
    else:
        # TODO(mg): inserting the username and password in the
        # uploaded file makes testing easy, but should not be done in
        # production. See issue #44.
        auth['authUrl'] = args.os_auth_url
        auth['tenant'] = args.os_tenant_name
        auth['username'] = args.os_username
        auth['password'] = args.os_password
    return auth


def deploy_project(args):
    version = args.auth_version
    conn = _get_zerocloud_conn(args)
    conn.authenticate()

    # We can now reset the auth for the web UI, if needed
    if args.no_ui_auth:
        version = '0.0'
    auth = _prepare_auth(version, args, conn)
    auth_opts = jinja2.Markup(json.dumps(auth))

    _deploy_zapp(conn, args.target, args.zapp, auth_opts)
    if args.execute:
        # for compatibility with the option name in 'zpm execute'
        args.container = args.target
        execute(args)

    LOG.info('app deployed to\n  %s/%s/' % (conn.url, args.target))


def execute(args):
    conn = _get_zerocloud_conn(args)

    job_filename = '%s.json' % os.path.splitext(args.zapp)[0]
    try:
        headers, content = conn.get_object(args.container, job_filename)
    except swiftclient.ClientException as exc:
        if exc.http_status == 404:
            raise zpmlib.ZPMException("Could not find %s" % exc.http_path)
        else:
            raise zpmlib.ZPMException(str(exc))
    job = json.loads(content)
    conn.post_job(job)

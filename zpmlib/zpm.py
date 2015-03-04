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
import json
import os
import shlex
import sys
import tarfile
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import jinja2
import prettytable
import six
import swiftclient
import yaml

import zpmlib
from zpmlib import util
from zpmlib import zappbundler
from zpmlib import zapptemplate

_DEFAULT_UI_TEMPLATES = ['index.html.tmpl', 'style.css', 'zerocloud.js']
_ZAPP_YAML = 'python-zapp.yaml'
_ZAPP_WITH_UI_YAML = 'python-zapp-with-ui.yaml'

LOG = zpmlib.get_logger(__name__)
BUFFER_SIZE = 65536
#: path/filename of the system.map (job description) in every zapp
SYSTEM_MAP_ZAPP_PATH = 'boot/system.map'

#: Message displayed if insufficient auth settings are specified, either on the
#: command line or in environment variables. Shamelessly copied from
#: ``python-swiftclient``.
NO_AUTH_MSG = """\
Auth version 1.0 requires ST_AUTH, ST_USER, and ST_KEY environment variables
to be set or overridden with -A, -U, or -K.

Auth version 2.0 requires OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, and
OS_TENANT_NAME OS_TENANT_ID to be set or overridden with --os-auth-url,
--os-username, --os-password, --os-tenant-name or os-tenant-id. Note:
adding "-V 2" is necessary for this."""

#: Column labels for the execution summary table
EXEC_TABLE_HEADER = [
    'Node',
    'Status',
    'Retcode',
    'NodeT',
    'SysT',
    'UserT',
    'DiskReads',
    'DiskBytesR',
    'DiskWrites',
    'DiskBytesW',
    'NetworkReads',
    'NetworkBytesR',
    'NetworkWrites',
    'NetworkBytesW',
]


def create_project(location, with_ui=False, template=None):
    """
    Create a ZeroVM application project by writing a default `zapp.yaml` in the
    specified directory `location`.

    :param location:
            Directory location to place project files.
    :param with_ui:
        Defaults to `False`. If `True`, add basic UI template files as well to
        ``location``.
    :param template:
        Default: ``None``. If no template is specified, use the default project
        template. (See `zpmlib.zapptemplate`.)

    :returns: List of created project files.
    """
    if os.path.exists(location):
        if not os.path.isdir(location):
            # target must be an empty directory
            raise RuntimeError("Target `location` must be a directory")
    else:
        os.makedirs(location)

    # Run the template builder, and create additional files for the project by
    # the type. If ``template`` is none, this is essientially a NOP.
    # TODO: just use the afc._created_files
    created_files = []
    with util.AtomicFileCreator() as afc:
        for file_type, path, contents in zapptemplate.template(
                location, template, with_ui=with_ui):
            afc.create_file(file_type, path, contents)
            created_files.append(path)
    return created_files


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
    Generate the boot/system.map file contents from the zapp config file.

    :param zapp:
        `dict` of the contents of a ``zapp.yaml`` file.
    :returns:
        `dict` of the job description
    """
    job = []

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
        # Copy everything, but handle 'env', 'path', and 'args' specially:
        jgroup = dict(zgroup)

        path = zgroup['path']
        # if path is `file://image:exe`, exec->name is "exe"
        # if path is `swift://~/container/obj`, exec->name is "obj"
        exec_name = None
        if path.startswith('file://'):
            exec_name = path.split(':')[-1]
        elif path.startswith('swift://'):
            # If obj is a pseudo path, like foo/bar/obj, we need to
            # handle this as well with a careful split.
            # If the object path is something like `swift://~/container/obj`,
            # then exec_name will be `obj`.
            # If the object path is something like
            # `swift://./container/foo/bar/obj`, then the exec_name will be
            # `foo/bar/obj`.
            exec_name = path.split('/', 4)[-1]

        jgroup['exec'] = {
            'path': zgroup['path'],
            'args': translate_args(zgroup['args']),
        }
        if exec_name is not None:
            jgroup['exec']['name'] = exec_name

        del jgroup['path'], jgroup['args']

        if 'env' in zgroup:
            jgroup['exec']['env'] = zgroup['env']
            del jgroup['env']
        job.append(jgroup)
    return job


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
        Extracted contents of the boot/system.map with the swift
        path to the .zapp added to the `devices` for each `group`.

        So if the job looks like this::

            [{'exec': {'args': 'hello.py', 'path': 'file://python2.7:python'},
              'devices': [{'name': 'python2.7'}, {'name': 'stdout'}],
              'name': 'hello'}]

        the output will look like something like this::

            [{'exec': {u'args': 'hello.py', 'path': 'file://python2.7:python'},
              'devices': [
                {'name': 'python2.7'},
                {'name': 'stdout'},
                {'name': 'image',
                 'path': 'swift://AUTH_abcdef123/test_container/hello.zapp'},
              ],
              'name': 'hello'}]


    """
    fp = tar.extractfile(SYSTEM_MAP_ZAPP_PATH)
    # NOTE(larsbutler): the `decode` is needed for python3
    # compatibility
    job = json.loads(fp.read().decode('utf-8'))
    device = {'name': 'image', 'path': zapp_swift_url}
    for group in job:
        group['devices'].append(device)

    return job


def bundle_project(root, refresh_deps=False):
    """
    Bundle the project under root.
    """
    zapp_yaml = os.path.join(root, 'zapp.yaml')
    zapp = yaml.safe_load(open(zapp_yaml))

    zapp_name = zapp['meta']['name'] + '.zapp'

    zapp_tar_path = os.path.join(root, zapp_name)
    tar = tarfile.open(zapp_tar_path, 'w:gz')

    job = _generate_job_desc(zapp)
    job_json = json.dumps(job)
    info = tarfile.TarInfo(name='boot/system.map')
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

    # Do template-specific bundling
    zappbundler.bundle(root, zapp, tar, refresh_deps=refresh_deps)
    tar.close()
    print('created %s' % zapp_name)


def _add_file_to_tar(root, path, tar, arcname=None):
    """
    :param root:
        Root working directory.
    :param path:
        File path.
    :param tar:
        Open :class:`tarfile.TarFile` object to add the ``files`` to.
    """
    # TODO(larsbutler): document ``arcname``
    LOG.info('adding %s' % path)
    path = os.path.join(root, path)
    relpath = os.path.relpath(path, root)
    if arcname is None:
        # In the archive, give the file the same name and path.
        arcname = relpath
    tar.add(path, arcname=arcname)


def _find_ui_uploads(zapp, tar):
    matches = set()
    names = tar.getnames()
    for pattern in zapp.get('ui', []):
        matches.update(fnmatch.filter(names, pattern))
    return sorted(matches)


def _post_job(url, token, data, http_conn=None, response_dict=None,
              content_type='application/json', content_length=None,
              response_body_buffer=None):
    # Modelled after swiftclient.client.post_account.
    headers = {'X-Auth-Token': token,
               'X-Zerovm-Execute': '1.0',
               'Content-Type': content_type}
    if content_length:
        headers['Content-Length'] = str(content_length)

    if http_conn:
        parsed, conn = http_conn
    else:
        parsed, conn = swiftclient.http_connection(url)

    conn.request('POST', parsed.path, data, headers)
    resp = conn.getresponse()
    body = resp.read()
    swiftclient.http_log((url, 'POST'), {'headers': headers}, resp, body)
    swiftclient.store_response(resp, response_dict)

    if response_body_buffer is not None:
        response_body_buffer.write(body)


class ZeroCloudConnection(swiftclient.Connection):
    """
    An extension of the `swiftclient.Connection` which has the capability of
    posting ZeroVM jobs to an instance of ZeroCloud (running on Swift).
    """

    def authenticate(self):
        """
        Authenticate with the provided credentials and cache the storage URL
        and auth token as `self.url` and `self.token`, respectively.
        """
        self.url, self.token = self.get_auth()

    def post_job(self, job, response_dict=None, response_body_buffer=None):
        """Start a ZeroVM job, using a pre-uploaded zapp

        :param object job:
            Job description. This will be encoded as JSON and sent to
            ZeroCloud.
        """
        json_data = json.dumps(job)
        LOG.debug('JOB: %s' % json_data)
        return self._retry(None, _post_job, json_data,
                           response_dict=response_dict,
                           response_body_buffer=response_body_buffer)

    def post_zapp(self, data, response_dict=None, content_length=None,
                  response_body_buffer=None):
        return self._retry(None, _post_job, data,
                           response_dict=response_dict,
                           content_type='application/x-gzip',
                           content_length=content_length,
                           response_body_buffer=response_body_buffer)


def _get_zerocloud_conn(args):
    version = args.auth_version
    # no version was explicitly requested; try to guess it:
    if version is None:
        version = _guess_auth_version(args)

    if version == '1.0':
        if any([arg is None for arg in (args.auth, args.user, args.key)]):
            raise zpmlib.ZPMException(
                "Version 1 auth requires `--auth`, `--user`, and `--key`."
                "\nSee `zpm deploy --help` for more information."
            )

        conn = ZeroCloudConnection(args.auth, args.user, args.key)
    elif version == '2.0':
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
    else:
        raise zpmlib.ZPMException(NO_AUTH_MSG)

    return conn


def _deploy_zapp(conn, target, zapp_path, auth_opts, force=False):
    """Upload all of the necessary files for a zapp.

    Returns the name an uploaded index file, or the target if no
    index.html file was uploaded.

    :param bool force:
        Force deployment, even if the target container is not empty. This means
        that files could be overwritten and could cause consistency problems
        with these objects in Swift.
    """
    base_container = target.split('/')[0]
    try:
        _, objects = conn.get_container(base_container)
        if not len(objects) == 0:
            if not force:
                raise zpmlib.ZPMException(
                    "Target container ('%s') is not empty.\nDeploying to a "
                    "non-empty container can cause consistency problems with "
                    "overwritten objects.\nSpecify the flag `--force/-f` to "
                    "overwrite anyway."
                    % base_container
                )
    except swiftclient.exceptions.ClientException:
        # container doesn't exist; create it
        LOG.info("Container '%s' not found. Creating it...", base_container)
        conn.put_container(base_container)

    # If we get here, everything with the container is fine.
    index = target + '/'
    uploads = _generate_uploads(conn, target, zapp_path, auth_opts)
    for path, data, content_type in uploads:
        if path.endswith('/index.html'):
            index = path
        container, obj = path.split('/', 1)
        conn.put_object(container, obj, data, content_type=content_type)
    return index


def _generate_uploads(conn, target, zapp_path, auth_opts):
    """Generate sequence of (container-and-file-path, data, content-type)
    tuples.
    """
    tar = tarfile.open(zapp_path, 'r:gz')
    zapp_config = yaml.safe_load(tar.extractfile('zapp.yaml'))

    remote_zapp_path = '%s/%s' % (target, os.path.basename(zapp_path))
    swift_url = _get_swift_zapp_url(conn.url, remote_zapp_path)
    job = _prepare_job(tar, zapp_config, swift_url)

    yield (remote_zapp_path, gzip.open(zapp_path).read(), 'application/x-tar')
    yield ('%s/%s' % (target, SYSTEM_MAP_ZAPP_PATH), json.dumps(job),
           'application/json')

    for path in _find_ui_uploads(zapp_config, tar):
        output = tar.extractfile(path).read()
        if path.endswith('.tmpl'):
            tmpl = jinja2.Template(output.decode('utf-8'))
            output = tmpl.render(auth_opts=auth_opts, zapp=zapp_config)
            # drop the .tmpl extension
            path = os.path.splitext(path)[0]

        ui_path = '%s/%s' % (target, path)
        yield (ui_path, output, None)


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
    version = str(float(version))
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
        # production. See issue #46.
        auth['authUrl'] = args.os_auth_url
        auth['tenant'] = args.os_tenant_name
        auth['username'] = args.os_username
        auth['password'] = args.os_password
    return auth


def _guess_auth_version(args):
    """Guess the auth version from first the command line args and/or envvars.

    Command line arguments override environment variables, so we check those
    first.

    Auth v1 arguments:

    * ``--auth``
    * ``--user``
    * ``--key``

    Auth v2 arguments:

    * ``--os-auth-url``
    * ``--os-username``
    * ``--os-password``
    * ``--os-tenant-name``

    If all of the v1 and v2 arguments are specified, default to 1.0 (this is
    how ``python-swiftclient`` behaves).

    If no auth version can be determined from the command line args, we check
    environment variables.

    Auth v1 vars:

    * ``ST_AUTH``
    * ``ST_USER``
    * ``ST_KEY``

    Auth v2 vars:

    * ``OS_AUTH_URL``
    * ``OS_USERNAME``
    * ``OS_PASSWORD``
    * ``OS_TENANT_NAME``

    The same rule above applies; if both sets of variables are specified,
    default to 1.0.

    If no auth version can be determined, return `None`.

    :param args:
        :class:`argparse.Namespace`, representing the args specified on the
        command line.
    :returns: '1.0', '2.0', or ``None``
    """
    v1 = (args.auth, args.user, args.key)
    v2 = (args.os_auth_url, args.os_username, args.os_password,
          args.os_tenant_name)

    if all(v1) and not all(v2):
        return '1.0'
    elif all(v2) and not all(v1):
        return '2.0'
    elif all(v1) and all(v2):
        # All vars for v1 and v2 auth are set, so we follow the
        # `python-swiftclient` behavior and default to 1.0.
        return '1.0'
    else:
        # deduce from envvars
        env = os.environ
        v1_env = (env.get('ST_AUTH'), env.get('ST_USER'), env.get('ST_KEY'))
        v2_env = (env.get('OS_AUTH_URL'), env.get('OS_USERNAME'),
                  env.get('OS_PASSWORD'), env.get('OS_TENANT_NAME'))
        if all(v1_env) and not all(v2_env):
            return '1.0'
        if all(v2_env) and not all(v1_env):
            return '2.0'
        elif all(v1_env) and all(v2_env):
            # Same as above, if all v1 and v2 vars are set, default to 1.0.
            return '1.0'
        else:
            # Insufficient auth details have been specified.
            return None


def deploy_project(args):
    conn = _get_zerocloud_conn(args)
    conn.authenticate()
    ui_auth_version = conn.auth_version

    # We can now reset the auth for the web UI, if needed
    if args.no_ui_auth:
        ui_auth_version = '0.0'

    auth = _prepare_auth(ui_auth_version, args, conn)
    auth_opts = jinja2.Markup(json.dumps(auth))

    deploy_index = _deploy_zapp(conn, args.target, args.zapp, auth_opts,
                                force=args.force)

    print('app deployed to\n  %s/%s' % (conn.url, deploy_index))

    if args.execute:
        # for compatibility with the option name in 'zpm execute'
        args.container = args.target
        resp_body_buffer = BytesIO()
        resp = execute(args, response_body_buffer=resp_body_buffer)
        resp_body_buffer.seek(0)

        if resp['status'] < 200 or resp['status'] >= 300:
            raise zpmlib.ZPMException(resp_body_buffer.read())

        if args.summary:
            total_time, exec_table = _get_exec_table(resp)
            print('Execution summary:')
            print(exec_table)
            print('Total time: %s' % total_time)

        sys.stdout.write(resp_body_buffer.read())


def _get_exec_table(resp):
    """Build an execution summary table from a job execution response.

    :param dict resp:
        Response dictionary from job execution. Must contain a ``headers`` key
        at least (and will typically contain ``status`` and ``reason`` as
        well).
    :returns:
        Tuple of total execution time (`str`),
        ``prettytable.PrettyTable`` containing the summary of all node
        executions in the job.
    """
    headers = resp['headers']
    total_time, table_data = _get_exec_table_data(headers)

    table = prettytable.PrettyTable(EXEC_TABLE_HEADER)

    for row in table_data:
        table.add_row(row)

    return total_time, table


def _get_exec_table_data(headers):
    """Extract a stats table from execution HTTP response headers.

    Stats include things like node name, execution time, number of
    reads/writes, bytes read/written, etc.

    :param dict headers:
        `dict` of response headers from a job execution request. It must
        contain at least ``x-nexe-system``, ``x-nexe-status``,
        ``x-nexe-retcode``, ``x-nexe-cdr-line``.
    :returns:
        Tuple of two items. The first is the total time for the executed job
        (as a `str`). The second is a table (2d `list`) of execution data
        extracted from ``X-Nexe-System`` and ``X-Nexe-Cdr-Line`` headers.

        Each row in the table consists of the following data:

            * node name
            * node time
            * system time
            * user time
            * number of disk reads
            * number of bytes read from disk
            * number of disk writes
            * number of bytes written to disk
            * number of network reads
            * number of bytes read from network
            * number of network writes
            * number of bytes written to network
    """
    node_names = iter(headers['x-nexe-system'].split(','))
    statuses = iter(headers['x-nexe-status'].split(','))
    retcodes = iter(headers['x-nexe-retcode'].split(','))

    cdr = headers['x-nexe-cdr-line']
    cdr_data = [x.strip() for x in cdr.split(',')]
    total_time = cdr_data.pop(0)
    cdr_data = iter(cdr_data)

    def adviter(x):
        return six.advance_iterator(x)

    table_data = []
    while True:
        try:
            node_name = adviter(node_names)
            status = adviter(statuses)
            retcode = adviter(retcodes)
            node_time = adviter(cdr_data)
            cdr = adviter(cdr_data).split()
            row = [node_name, status, retcode, node_time] + cdr
            table_data.append(row)
        except StopIteration:
            break
    return total_time, table_data


def execute(args, response_body_buffer=None):
    """Execute a zapp remotely on a ZeroCloud deployment.

    :returns:
        A `dict` with response data, including the keys 'status', 'reason', and
        'headers'.
    """
    conn = _get_zerocloud_conn(args)

    resp = dict()
    if args.container:
        job_filename = SYSTEM_MAP_ZAPP_PATH
        try:
            headers, content = conn.get_object(args.container, job_filename)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                raise zpmlib.ZPMException("Could not find %s" % exc.http_path)
            else:
                raise zpmlib.ZPMException(str(exc))
        job = json.loads(content)

        conn.post_job(job, response_dict=resp,
                      response_body_buffer=response_body_buffer)
        LOG.debug('RESP STATUS: %s %s', resp['status'], resp['reason'])
        LOG.debug('RESP HEADERS: %s', resp['headers'])
    else:
        size = os.path.getsize(args.zapp)
        zapp_file = open(args.zapp, 'rb')
        data_reader = iter(lambda: zapp_file.read(BUFFER_SIZE), b'')
        conn.post_zapp(data_reader, response_dict=resp, content_length=size,
                       response_body_buffer=response_body_buffer)
        zapp_file.close()
    return resp


def auth(args):
    conn = _get_zerocloud_conn(args)
    conn.authenticate()

    print('Auth token: %s' % conn.token)
    print('Storage URL: %s' % conn.url)

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

try:
    import configparser as ConfigParser
except ImportError:
    # Python 2 fallback
    import ConfigParser
import argparse
import array
import fcntl
import os
import re
import shutil
import stat
import sys
import tarfile
import termios
from pty import _read as pty_read
from pty import _copy as pty_copy
import pty
import threading
import tty

try:
    from collections import OrderedDict
except ImportError:
    # Python 2.6 fallback
    from ordereddict import OrderedDict

from os import path
from subprocess import Popen, PIPE
from tempfile import mkdtemp


ENV_MATCH = re.compile(r'([_A-Z0-9]+)=(.*)')
DEFAULT_MANIFEST = {
    'Version': '20130611',
    'Memory': '%d' % (4 * 1024 * 1024 * 1024),
    'Node': 1,
    'Timeout': 50
}
DEFAULT_LIMITS = {
    'reads': str(1024 * 1024 * 1024 * 4),
    'rbytes': str(1024 * 1024 * 1024 * 4),
    'writes': str(1024 * 1024 * 1024 * 4),
    'wbytes': str(1024 * 1024 * 1024 * 4)
}
CHANNEL_SEQ_READ_TEMPLATE = 'Channel = %s,%s,0,0,%s,%s,0,0'
CHANNEL_SEQ_WRITE_TEMPLATE = 'Channel = %s,%s,0,0,0,0,%s,%s'
CHANNEL_RANDOM_RW_TEMPLATE = 'Channel = %s,%s,3,0,%s,%s,%s,%s'
CHANNEL_RANDOM_RO_TEMPLATE = 'Channel = %s,%s,3,0,%s,%s,0,0'

DEBUG_TEMPLATE = '''set confirm off
b CreateSession
r
b main
add-symbol-file %s 0x440a00020000
shell clear
c
d br
'''

NVRAM_TEMPLATE = """\
[args]
args = %(args)s
[fstab]
%(fstab)s
[mapping]
%(mapping)s"""

CHANNEL_MAPPING_TEMPLATE = "channel=/dev/%s,mode=%s\n"

MANIFEST_TEMPLATE = """\
Node = %(node)s
Version = %(version)s
Timeout = %(timeout)s
Memory = %(memory)s
Program = %(program)s
%(channels)s"""

MANIFEST_DEFAULTS = dict(
    version='20130611',
    memory=4294967296,
    node=1,
    timeout=50,
)

GETS_DEFAULT = 4294967296
GET_SIZE_DEFAULT_BYTES = 4294967296
PUTS_DEFAULT = 4294967296
PUT_SIZE_DEFAULT_BYTES = 4294967296

SEQ_READ_SEQ_WRITE = 0
RND_READ_SEQ_WRITE = 1
SEQ_READ_RND_WRITE = 2
RND_READ_RND_WRITE = 3

_DEFAULT_MOUNT_DIR = '/'
_DEFAULT_MOUNT_ACCESS = 'ro'

ZEROVM_EXECUTABLE = 'zerovm'
ZEROVM_OPTIONS = '-PQ'
DEBUG_EXECUTABLE = 'zerovm-dbg'
DEBUG_OPTIONS = '-sPQ'
GDB = 'x86_64-nacl-gdb'


class Channel(object):
    """
    Definition of a channel within a manifest. Defines a mapping from the host
    to the ZeroVM filesystem, access type, and read/write limits.

    :param uri:
        Path to a local file, pipe, character device, tcp socket or host ID.
    :param alias:
        Path where this channel will be mounted in ZeroVM.
    :param access_type:
        Choose from the following:

            * 0: sequential read/ sequential write
            * 1: random read/ sequential write
            * 2: sequential read / random write
            * 3: random read / random write
    :param etag:
        etag switch; can be in the range 0..1

        Default: 0
    :param gets:
        Limit for number of reads from this channel.

        Default: 4294967296
    :param get_size:
        Limit on total amount of data to read from this channel, in bytes.

        Default: 4294967296
    :param puts:
        Limit for number of writes to this channel.

        Default: 4294967296
    :param put_size:
        Limit on total amount of data to be written to this channel, in bytes.

        Default: 4294967296
    """

    def __init__(self, uri, alias, access_type,
                 etag=0,
                 gets=GETS_DEFAULT,
                 get_size=GET_SIZE_DEFAULT_BYTES,
                 puts=PUTS_DEFAULT,
                 put_size=PUT_SIZE_DEFAULT_BYTES):
        self.uri = uri
        self.alias = alias
        self.access_type = access_type
        self.etag = etag
        self.gets = gets
        self.get_size = get_size
        self.puts = puts
        self.put_size = put_size

    def __str__(self):
        return 'Channel = %s,%s,%s,%s,%s,%s,%s,%s' % (
            self.uri, self.alias, self.access_type, self.etag,
            self.gets, self.get_size, self.puts, self.put_size
        )

    def __repr__(self):
        return '<%s>' % self.__str__()


class Manifest(object):
    """
    Object representation of a ZeroVM manifest. Includes utilities and sane
    defaults for generating manifest files.
    """
    DEFAULT_NODE = 1

    def __init__(self, version, timeout, memory, program, node=DEFAULT_NODE,
                 etag=0, channels=None):
        self.version = version
        self.timeout = timeout
        self.memory = memory
        self.program = program

        self.node = node
        self.etag = etag

        self.channels = channels
        if self.channels is None:
            self.channels = []

    @classmethod
    def default_manifest(cls, basedir, program):
        channels = [
            Channel('/dev/stdin', '/dev/stdin', SEQ_READ_SEQ_WRITE, puts=0,
                    put_size=0),
            Channel(path.join(basedir, 'stdout.%s' % cls.DEFAULT_NODE),
                    '/dev/stdout', SEQ_READ_SEQ_WRITE, gets=0, get_size=0),
            Channel(path.join(basedir, 'stderr.%s' % cls.DEFAULT_NODE),
                    '/dev/stderr', SEQ_READ_SEQ_WRITE, gets=0, get_size=0),
            Channel(path.join(basedir, 'nvram.%s' % cls.DEFAULT_NODE),
                    '/dev/nvram', RND_READ_RND_WRITE),
        ]
        return Manifest(MANIFEST_DEFAULTS['version'],
                        MANIFEST_DEFAULTS['timeout'],
                        MANIFEST_DEFAULTS['memory'],
                        program,
                        channels=channels)

    def dumps(self):
        """
        Get the text representation of the manifest.
        """
        if not self.channels:
            raise RuntimeError("Manifest must have at least 1 channel.")

        manifest = MANIFEST_TEMPLATE
        manifest %= dict(
            node=self.node,
            version=self.version,
            timeout=self.timeout,
            memory='%s,%s' % (self.memory, self.etag),
            program=self.program,
            channels='\n'.join([str(c) for c in self.channels]),
        )
        return manifest


class NVRAM(object):
    """
    :param program_args:
        A `list` of the command args to be run inside ZeroVM. In the case of a
        Python application, this would be something like:

            ['python', '-c', 'print "hello, world"']

    :param processed_images:
        A `list` 3-tuples containing (image path, mount point, access). See
        :func:`_process_images` for more details.

    :param env:
        Optional. `dict` of environment settings from zvsh.cfg.

    :param int debug_verbosity:
        Optional. Debug verbosity level, in the range 0..4.
    """

    def __init__(self, program_args, processed_images, env=None,
                 debug_verbosity=None):
        # TODO(larsbutler): What about the [debug] and [env] sections?
        self.program_args = program_args
        self.processed_images = processed_images
        self.env = env
        self.debug_verbosity = debug_verbosity

    def dumps(self):
        """
        Generate the text for an nvram file.
        """
        nvram_text = NVRAM_TEMPLATE
        fstab_channels = []
        for i, (zvm_image, mount_point, access) in enumerate(
                self.processed_images, start=1):
            device = '/dev/%s.%s' % (i, path.basename(zvm_image))
            fstab_channel = (
                'channel=%(device)s,mountpoint=%(mount_point)s,'
                'access=%(access)s,removable=no'
                % dict(device=device, mount_point=mount_point, access=access)
            )
            fstab_channels.append(fstab_channel)

        mapping = ''
        if sys.stdin.isatty():
            mapping += 'channel=/dev/stdin,mode=char\n'
        if sys.stdout.isatty():
            mapping += 'channel=/dev/stdout,mode=char\n'
        if sys.stderr.isatty():
            mapping += 'channel=/dev/stderr,mode=char\n'

        # When ZRT presents a program with its argv, it parses the
        # nvram file. This parser is very simple. It will choke on ','
        # (it treats comma the same as newline) and it will split the
        # command line on ' '. We must therefore escape each argument
        # individually before joining them.
        args = ' '.join(map(_nvram_escape, self.program_args))

        nvram_text %= dict(
            args=args,
            fstab='\n'.join(fstab_channels),
            mapping=mapping,
            env='\n'.join([]),
        )

        if self.env is not None:
            nvram_text += '[env]\n'
            for k, v in self.env.items():
                nvram_text += 'name=%s,value=%s\n' % (k, _nvram_escape(v))
        if self.debug_verbosity is not None:
            nvram_text += '[debug]\nverbosity=%s\n' % self.debug_verbosity

        return nvram_text


def _nvram_escape(value):
    r"""Escape value for inclusion as a value in a nvram file.

    The ini-file parser in ZRT is very simple. One quirk is that it
    handles ',' the same as '\n', which means that a value like

      greeting = Hello, World

    will be cut-off after "Hello".

    Values also need protection in other ways:

    * When "args" are loaded, the value is split on ' ' and each
      argument found is then unescaped. This means that each arg need
      to have ' ' escaped.

    * When a "value" is loaded in [env], it is unescaped. It must
      therefore also be escaped.

    This function escapes '\\', '"', ',', ' ', and '\n'. These are the
    characters that conf_parser::unescape_string_copy_to_dest is
    documented to handle and they are sufficient to handle the above
    use cases.

    >>> _nvram_escape('foo, bar')
    'foo\\x2c\\x20bar'
    >>> _nvram_escape('new\nline')
    'new\\x0aline'
    """
    for c in '\\", \n':
        value = value.replace(c, '\\x%02x' % ord(c))
    return value


def _process_images(zvm_images):
    """
    Process a list of the --zvm-image arguments and split them into the
    `path,mount_point,access_type` components. This returns a generator of
    3-tuples.

    `mount_point` and `access_type` are optional and will default to `/` and
    `ro`, respectively.

    Example:

    >>> list(_process_images(['/home/user1/foo.tar',
    ...                       '/home/user1/bar.tar,/var/lib',
    ...                       '/home/user1/baz.tar,/usr/lib,rw']))
    [('/home/user1/foo.tar', '/', 'ro'), \
('/home/user1/bar.tar', '/var/lib', 'ro'), \
('/home/user1/baz.tar', '/usr/lib', 'rw')]

    """
    for image in zvm_images:
        image_split = image.split(',')
        # mount_dir and access_type are optional,
        # so defaults are provided:
        mount_dir = _DEFAULT_MOUNT_DIR
        access_type = _DEFAULT_MOUNT_ACCESS

        if len(image_split) == 1:
            path = image_split[0]
        elif len(image_split) == 2:
            path, mount_dir = image_split
        elif len(image_split) == 3:
            path, mount_dir, access_type = image_split

        yield path, mount_dir, access_type


def create_manifest(working_dir, program_path, manifest_cfg, tar_files,
                    limits_cfg):
    """
    :param manifest_cfg:
        `dict` containing the following keys:

            * Node
            * Version
            * Timeout
            * Memory
    :param limits_cfg:
        `dict` containing the following keys:

            * reads
            * rbytes
            * writes
            * wbytes
    """
    manifest = Manifest.default_manifest(working_dir, program_path)
    manifest.node = manifest_cfg['Node']
    manifest.version = manifest_cfg['Version']
    manifest.timeout = manifest_cfg['Timeout']
    manifest.memory = manifest_cfg['Memory']

    for i, tar_file in enumerate(tar_files, start=1):
        mount_point = '/dev/%s.%s' % (i, path.basename(tar_file))

        ch = Channel(
            tar_file, mount_point, access_type=RND_READ_RND_WRITE,
            gets=limits_cfg['reads'],
            get_size=limits_cfg['rbytes'],
            puts=limits_cfg['writes'],
            put_size=limits_cfg['wbytes'],
        )
        manifest.channels.append(ch)

    return manifest


def _get_runtime_file_paths(working_dir, node):
    """
    Generate the runtime files paths for boot, manifest, nvram, stdout, and
    stderr files, and return them as a `OrderedDict` with the following
    structure:

    >>> _get_runtime_file_paths('/home/user1', 1)
    OrderedDict([('boot', '/home/user1/boot.1'), \
('manifest', '/home/user1/manifest.1'), \
('nvram', '/home/user1/nvram.1'), \
('stdout', '/home/user1/stdout.1'), \
('stderr', '/home/user1/stderr.1')])

    Note that that paths are created by simply joining `working_dir`, so
    relatve file paths can be used as well:

    >>> _get_runtime_file_paths('foo/', 1)
    OrderedDict([('boot', 'foo/boot.1'), \
('manifest', 'foo/manifest.1'), \
('nvram', 'foo/nvram.1'), \
('stdout', 'foo/stdout.1'), \
('stderr', 'foo/stderr.1')])
    """
    files = OrderedDict()
    for each in ('boot', 'manifest', 'nvram', 'stdout', 'stderr'):
        files[each] = path.join(working_dir, '%s.%s' % (each, node))

    return files


def _check_runtime_files(runtime_files):
    """
    Given a `dict` of runtime files (see the output
    :func:`_get_runtime_file_paths`), check if any exist. If any exist, raise
    a `RuntimeError`.
    """
    for file_path in runtime_files.values():
        if path.exists(file_path):
            raise RuntimeError("Unable to write '%s': file already exists"
                               % file_path)


def run_zerovm(zvconfig, zvargs):
    """
    :param zvconfig:
        :class:`ZvConfig` instance.
    :param zvargs:
        :class:`ZvArgs` instance.
    """
    if zvargs.args.zvm_save_dir is None:
        # use a temp dir
        working_dir = mkdtemp()
    else:
        # use the specified dir
        working_dir = path.abspath(zvargs.args.zvm_save_dir)

    if not path.exists(working_dir):
        os.makedirs(working_dir)
    # Manifest config options from the command line / zvsh.cfg
    man_cfg = zvconfig['manifest']
    node = man_cfg['Node']

    # These files will be generated in the `working_dir`.
    runtime_files = _get_runtime_file_paths(working_dir, node)
    # If any of these files already exist in the target dir,
    # we need to raise an error and halt.
    _check_runtime_files(runtime_files)

    os.mkfifo(runtime_files['stdout'])
    os.mkfifo(runtime_files['stderr'])

    processed_images = list(_process_images(zvargs.args.zvm_image))
    # expand the tar image paths to absolute paths.
    processed_images = [(path.abspath(tar_path), mp, access)
                        for tar_path, mp, access in processed_images]
    # Just the tar files:
    tar_files = [x[0] for x in processed_images]

    # Search the tar images and extract the target nexe to the specified file
    # (runtime_files['boot'])
    _extract_nexe(runtime_files['boot'], processed_images, zvargs.args.command)

    # Generate and write the manifest file:
    manifest = create_manifest(working_dir, runtime_files['boot'], man_cfg,
                               tar_files, zvconfig['limits'])
    with open(runtime_files['manifest'], 'w') as man_fp:
        man_fp.write(manifest.dumps())

    # Generate and write the nvram file:
    nvram = NVRAM([zvargs.args.command] + zvargs.args.cmd_args,
                  processed_images)
    with open(runtime_files['nvram'], 'w') as nvram_fp:
        nvram_fp.write(nvram.dumps())

    # Now that all required files are generated and in place, run:
    try:
        _run_zerovm(working_dir, runtime_files['manifest'],
                    runtime_files['stdout'], runtime_files['stderr'],
                    zvargs.args.zvm_trace, zvargs.args.zvm_getrc)
    finally:
        # If we're using a tempdir for the working files,
        # destroy the directory to clean up.
        if zvargs.args.zvm_save_dir is None:
            shutil.rmtree(working_dir)


def _run_zerovm(working_dir, manifest_path, stdout_path, stderr_path,
                zvm_trace, zvm_getrc):
    """
    :param working_dir:
        Working directory which contains files needed to run ZeroVM (manifest,
        nvram, etc.).
    :param manifest_path:
        Path to the ZeroVM manifest, which should be in `working_dir`.
    :param stdout_path:
        Path to the file into which stdout is written. This file should be in
        `working_dir`.
    :param stderr_path:
        Path to the file into which stderr is written. This file should be in
        `working_dir`.
    :param bool zvm_trace:
        If `True`, enable ZeroVM trace output into `./zvsh.trace.log`.
    :param bool zvm_getrc:
        If `True`, return the ZeroVM exit code instead of the application exit
        code.
    """
    zvm_run = ['zerovm', '-PQ']
    if zvm_trace:
        # TODO(larsbutler): This should not be hard-coded. Can we parameterize
        # this via the command line?
        trace_log = path.abspath('zvsh.trace.log')
        zvm_run.extend(['-T', trace_log])
    zvm_run.append(manifest_path)
    runner = ZvRunner(zvm_run, stdout_path, stderr_path, working_dir,
                      getrc=zvm_getrc)
    runner.run()


def _extract_nexe(program_path, processed_images, command):
    """
    Given a `command`, search through the listed tar images
    (`processed_images`) and extract the nexe matching `command` to the target
    `program_path` on the host file system.

    :param program_path:
        Location (including filename) which specifies the destination of the
        extracted nexe.
    :param processed_images:
        Output of :func:`_process_images`.
    :param command:
        The name of a nexe, such as `python` or `myapp.nexe`.
    """
    with open(program_path, 'w') as program_fp:
        for zvm_image, _, _ in processed_images:
            try:
                tf = tarfile.open(zvm_image)
                nexe_fp = tf.extractfile(command)
                # once we've found the nexe the user wants to run,
                # we're done
                program_fp.write(nexe_fp.read())
                return program_path
            except KeyError:
                # program not found in this image,
                # go to the next and keep searching
                pass
            finally:
                tf.close()


class ZvArgs:
    """
    :attr parser:
        :class:`argparse.ArgumentParser` instance, used to define the command
        line arguments.
    :attr args:
        :class:`argparse.Namespace` representing the command line arguments.
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter
        )
        self.args = None
        self.add_agruments()

    def add_agruments(self):
        self.parser.add_argument(
            'command',
            help=('Zvsh command, can be:\n'
                  '- path to ZeroVM executable\n'
                  '- "gdb" (for running debugger)\n'),
        )
        self.parser.add_argument(
            '--zvm-image',
            help=('ZeroVM image file(s) in the following '
                  'format:\npath[,mount point][,access type]\n'
                  'defaults: path,/,ro\n'),
            action='append',
        )
        self.parser.add_argument(
            '--zvm-debug',
            help='Enable ZeroVM debug output into zvsh.log\n',
            action='store_true',
        )
        self.parser.add_argument(
            '--zvm-trace',
            help='Enable ZeroVM trace output into zvsh.trace.log\n',
            action='store_true',
        )
        self.parser.add_argument(
            '--zvm-verbosity',
            help='ZeroVM debug verbosity level\n',
            type=int,
        )
        self.parser.add_argument(
            '--zvm-getrc',
            help=('If set, zvsh will exit with '
                  'zerovm return code and not the application one\n'),
            action='store_true',
        )
        self.parser.add_argument(
            '--zvm-save-dir',
            help=('Save ZeroVM environment files into provided directory'),
            action='store',
        )
        self.parser.add_argument(
            'cmd_args',
            help='command line arguments\n',
            nargs=argparse.REMAINDER,
        )

    def parse(self, zvsh_args):
        self.args = self.parser.parse_args(args=zvsh_args)


class DebugArgs(ZvArgs):

    def parse(self, zvsh_args):
        self.args = self.parser.parse_args(args=zvsh_args)
        self.args.gdb_args = []
        while self.args.cmd_args:
            arg = self.args.cmd_args.pop(0)
            if arg == '--args':
                break
            self.args.gdb_args.append(arg)
        self.args.command = self.args.cmd_args.pop(0)


class ZvConfig(ConfigParser.ConfigParser):

    def __init__(self):
        ConfigParser.ConfigParser.__init__(self)
        self.add_section('manifest')
        self.add_section('env')
        self.add_section('limits')
        self.add_section('fstab')
        self.add_section('zvapp')
        self._sections['manifest'].update(DEFAULT_MANIFEST)
        self._sections['limits'].update(DEFAULT_LIMITS)
        self.optionxform = str

    def __getitem__(self, item):
        return self._sections[item]

    def __setitem__(self, key, value):
        self._sections[key] = value


class ZvShell(object):

    def __init__(self, config, savedir=None):
        self.temp_files = []
        self.nvram_fstab = []
        self.nvram_args = None
        self.nvram_filename = None
        self.nvram_reg_files = []
        self.program = None
        self.savedir = None
        self.tmpdir = None
        self.config = config
        self.savedir = savedir
        if self.savedir:
            # user specified a savedir
            self.tmpdir = self.savedir
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir)
        else:
            self.tmpdir = mkdtemp()
        self.node_id = self.config['manifest']['Node']
        self.config['manifest']['Memory'] += ',0'
        self.stdout = os.path.join(self.tmpdir, 'stdout.%d' % self.node_id)
        self.stderr = os.path.join(self.tmpdir, 'stderr.%d' % self.node_id)
        stdin = '/dev/stdin'
        self.channel_seq_read_template = CHANNEL_SEQ_READ_TEMPLATE \
            % ('%s', '%s', self.config['limits']['reads'],
               self.config['limits']['rbytes'])
        self.channel_seq_write_template = CHANNEL_SEQ_WRITE_TEMPLATE \
            % ('%s', '%s', self.config['limits']['writes'],
               self.config['limits']['wbytes'])
        self.channel_random_ro_template = CHANNEL_RANDOM_RO_TEMPLATE \
            % ('%s', '%s', self.config['limits']['reads'],
               self.config['limits']['rbytes'])
        self.channel_random_rw_template = CHANNEL_RANDOM_RW_TEMPLATE \
            % ('%s', '%s', self.config['limits']['reads'],
               self.config['limits']['rbytes'],
               self.config['limits']['writes'],
               self.config['limits']['wbytes'])
        self.manifest_channels = [
            self.channel_seq_read_template % (stdin, '/dev/stdin'),
            self.channel_seq_write_template % (os.path.abspath(self.stdout),
                                               '/dev/stdout'),
            self.channel_seq_write_template % (os.path.abspath(self.stderr),
                                               '/dev/stderr')
        ]
        for k, v in self.config['fstab'].items():
            self.nvram_fstab[self.create_manifest_channel(k)] = v

    def create_manifest_channel(self, file_name):
        name = os.path.basename(file_name)
        self.temp_files.append(file_name)
        devname = '/dev/%s.%s' % (len(self.temp_files), name)
        abs_path = os.path.abspath(file_name)
        if not os.path.exists(abs_path):
            fd = open(abs_path, 'wb')
            fd.close()
        if os.access(abs_path, os.W_OK):
            self.manifest_channels.append(self.channel_random_rw_template
                                          % (abs_path, devname))
        else:
            self.manifest_channels.append(self.channel_random_ro_template
                                          % (abs_path, devname))
        return devname

    def add_untrusted_args(self, program, cmdline):
        self.program = program
        untrusted_args = [os.path.basename(program)]
        for arg in cmdline:
            if arg.startswith('@'):
                arg = arg[1:]
                m = ENV_MATCH.match(arg)
                if m:
                    self.config['env'][m.group(1)] = m.group(2)
                else:
                    dev_name = self.create_manifest_channel(arg)
                    self.nvram_reg_files.append(dev_name)
                    untrusted_args.append(dev_name)
            else:
                untrusted_args.append(arg)

        self.nvram_args = {
            'args': untrusted_args
        }

    def add_image_args(self, zvm_image):
        if not zvm_image:
            return
        img_cache = {}
        for img in zvm_image:
            (imgpath, imgmp, imgacc) = (img.split(',') + [None] * 3)[:3]
            dev_name = img_cache.get(imgpath)
            if not dev_name:
                dev_name = self.create_manifest_channel(imgpath)
                img_cache[imgpath] = dev_name
            self.nvram_fstab.append((dev_name, imgmp or '/',  imgacc or 'ro'))
            nexe = None
            try:
                tar = tarfile.open(name=imgpath)
                nexe = tar.extractfile(self.program)
                tmpnexe_fn = os.path.join(self.tmpdir,
                                          'boot.%d' % self.node_id)
                tmpnexe_fd = open(tmpnexe_fn, 'wb')
                read_iter = iter(lambda: nexe.read(65535), b'')
                for chunk in read_iter:
                    tmpnexe_fd.write(chunk)
                tmpnexe_fd.close()
                self.program = tmpnexe_fn
            except (KeyError, tarfile.ReadError):
                pass

    def add_debug(self, zvm_debug):
        if zvm_debug:
            self.manifest_channels.append(self.channel_seq_write_template
                                          % (os.path.abspath('zvsh.log'),
                                             '/dev/debug'))

    def add_self(self):
        self.manifest_channels.append(self.channel_random_ro_template
                                      % (os.path.abspath(self.program),
                                         '/dev/self'))

    def create_nvram(self, verbosity):
        nvram = '[args]\n'
        nvram += 'args = %s\n' % ' '.join(
            ['%s' % a.replace(',', '\\x2c').replace(' ', '\\x20')
             for a in self.nvram_args['args']])
        if len(self.config['env']) > 0:
            nvram += '[env]\n'
            for k, v in self.config['env'].items():
                nvram += 'name=%s,value=%s\n' % (k, v.replace(',', '\\x2c'))
        if len(self.nvram_fstab) > 0:
            nvram += '[fstab]\n'
            for channel, mp, access in self.nvram_fstab:
                nvram += ('channel=%s,mountpoint=%s,access=%s,removable=no\n'
                          % (channel, mp, access))
        mapping = ''
        for std_name in ('stdin', 'stdout', 'stderr'):
            std_chan = getattr(sys, std_name)
            if std_chan.isatty():
                mapping += CHANNEL_MAPPING_TEMPLATE % (std_name, 'char')
            else:
                mapping += CHANNEL_MAPPING_TEMPLATE % (std_name, 'file')
        for dev in self.nvram_reg_files:
            mapping += 'channel=%s,mode=file\n' % dev
        if mapping:
            nvram += '[mapping]\n' + mapping
        if verbosity:
            nvram += '[debug]\nverbosity=%d\n' % verbosity
        self.nvram_filename = os.path.join(self.tmpdir,
                                           'nvram.%d' % self.node_id)
        nvram_fd = open(self.nvram_filename, 'wb')
        nvram_fd.write(nvram.encode('utf-8'))
        nvram_fd.close()

    def create_manifest(self):
        manifest = ''
        for k, v in self.config['manifest'].items():
            manifest += '%s = %s\n' % (k, v)
        manifest += 'Program = %s\n' % os.path.abspath(self.program)
        self.manifest_channels.append(self.channel_random_rw_template
                                      % (os.path.abspath(self.nvram_filename),
                                         '/dev/nvram'))
        manifest += '\n'.join(self.manifest_channels)
        manifest_fn = os.path.join(self.tmpdir, 'manifest.%d' % self.node_id)
        manifest_fd = open(manifest_fn, 'wb')
        manifest_fd.write(manifest.encode('utf-8'))
        manifest_fd.close()
        return manifest_fn

    def add_arguments(self, args):
        self.add_debug(args.zvm_debug)
        self.add_untrusted_args(args.command, args.cmd_args)
        self.add_image_args(args.zvm_image)
        self.add_self()
        self.create_nvram(args.zvm_verbosity)
        manifest_file = self.create_manifest()
        return manifest_file

    def cleanup(self):
        if not self.savedir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def add_debug_script(self):
        exec_path = os.path.abspath(self.program)
        debug_scp = DEBUG_TEMPLATE % exec_path
        debug_scp_fn = os.path.join(self.tmpdir, 'debug.scp')
        debug_scp_fd = open(debug_scp_fn, 'wb')
        debug_scp_fd.write(debug_scp)
        debug_scp_fd.close()
        return debug_scp_fn


def parse_return_code(report):
    rc = report.split('\n', 5)[2]
    try:
        rc = int(rc)
    except ValueError:
        rc = int(rc.replace('user return code = ', ''))
    return rc


class ZvRunner:

    def __init__(self, command_line, stdout, stderr, tempdir, getrc=False):
        self.command = command_line
        self.tmpdir = tempdir
        self.process = None
        self.stdout = stdout
        self.stderr = stderr
        self.getrc = getrc
        self.report = ''
        self.rc = -255
        # create std{out,err} unless they already exist:
        for stdfile in (self.stdout, self.stderr):
            if not os.path.exists(stdfile):
                os.mkfifo(stdfile)

    def run(self):
        try:
            self.process = Popen(self.command, stdin=PIPE, stdout=PIPE)
            self.spawn(True, self.stdin_reader)
            err_reader = self.spawn(True, self.stderr_reader)
            rep_reader = self.spawn(True, self.report_reader)
            writer = self.spawn(True, self.stdout_write)
            self.process.wait()
            rep_reader.join()
            self.rc = parse_return_code(self.report)
            if self.process.returncode == 0:
                writer.join()
                err_reader.join()
        except (KeyboardInterrupt, Exception):
            pass
        finally:
            if self.process:
                self.process.wait()
                if self.process.returncode > 0:
                    self.print_error(self.process.returncode)
            rc = self.rc
            if self.getrc:
                rc = self.process.returncode
            else:
                rc |= self.process.returncode << 4
            sys.exit(rc)

    def stdin_reader(self):
        if sys.stdin.isatty():
            try:
                for l in sys.stdin:
                    self.process.stdin.write(l)
            except IOError:
                pass
        else:
            try:
                for l in iter(lambda: sys.stdin.read(65535), b''):
                    self.process.stdin.write(l)
            except IOError:
                pass
        self.process.stdin.close()

    def stderr_reader(self):
        err = open(self.stderr)
        try:
            for l in iter(lambda: err.read(65535), b''):
                sys.stderr.write(l)
        except IOError:
            pass
        err.close()

    def stdout_write(self):
        pipe = open(self.stdout)
        if sys.stdout.isatty():
            for line in pipe:
                sys.stdout.write(line)
        else:
            for line in iter(lambda: pipe.read(65535), b''):
                sys.stdout.write(line)
        pipe.close()

    def report_reader(self):
        for line in iter(lambda: self.process.stdout.read(65535), b''):
            self.report += line

    def spawn(self, daemon, func, **kwargs):
        thread = threading.Thread(target=func, kwargs=kwargs)
        thread.daemon = daemon
        thread.start()
        return thread

    def print_error(self, rc):
        for f in os.listdir(self.tmpdir):
            path = os.path.join(self.tmpdir, f)
            if stat.S_ISREG(os.stat(path).st_mode):
                if is_binary_string(open(path).read(1024)):
                    sys.stderr.write('%s is a binary file\n' % path)
                else:
                    sys.stderr.write('\n'.join(['-' * 10 + f + '-' * 10,
                                                open(path).read(), '-' * 25,
                                                '']))
        sys.stderr.write(self.report)
        sys.stderr.write("ERROR: ZeroVM return code is %d\n" % rc)


def is_binary_string(byte_string):
    textchars = ''.join(
        map(chr, [7, 8, 9, 10, 12, 13, 27] + list(range(0x20, 0x100)))
    )
    return bool(set(byte_string) - set(textchars))


def spawn(argv, master_read=pty_read, stdin_read=pty_read):
    """Create a spawned process.
    Based on pty.spawn code."""
    # TODO(larsbutler): This type check won't work with python3
    # See http://packages.python.org/six/#six.string_types
    # for a possible solution.
    if isinstance(argv, (basestring)):
        argv = (argv,)
    pid, master_fd = pty.fork()
    if pid == pty.CHILD:
        os.execlp(argv[0], *argv)
    try:
        mode = tty.tcgetattr(pty.STDIN_FILENO)
        tty.setraw(pty.STDIN_FILENO)
        restore = 1
    except tty.error:    # This is the same as termios.error
        restore = 0
    # get pseudo-terminal window size
    buf = array.array('h', [0, 0, 0, 0])
    fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
    # pass window size settings to forked one
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)
    try:
        pty_copy(master_fd, master_read, stdin_read)
    except (IOError, OSError):
        if restore:
            tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)

    os.close(master_fd)


class Shell(object):
    def __init__(self, cmd_line, args=None):
        """
        :param str cmd_line:
            The full shell command; executable and args. (Like `zvsh
            --zvm-image python.tar python --version`, etc.)
        :param args:
            :class:`argparse.Namespace` instance. Optional. If not specified,
            arguments will be parsed from ``cmd_line``.
        """
        self.cmd_line = cmd_line

        if args is not None:
            self.args = args
        else:
            zvsh_args = ZvArgs()
            zvsh_args.parse(cmd_line[1:])
            self.args = zvsh_args.args
        zvsh_config = ['zvsh.cfg',
                       os.path.expanduser('~/.zvsh.cfg'),
                       '/etc/zvsh.cfg']
        self.config = ZvConfig()
        self.config.read(zvsh_config)
        self.zvsh = None

    def run(self):
        if 'gdb' == self.args.command:
            self._run_gdb()
        else:
            self._run_zvsh()

    def _run_zvsh(self):
        self.zvsh = ZvShell(self.config, self.args.zvm_save_dir)
        manifest_file = self.zvsh.add_arguments(self.args)
        zvm_run = [ZEROVM_EXECUTABLE, ZEROVM_OPTIONS]
        if self.args.zvm_trace:
            trace_log = os.path.abspath('zvsh.trace.log')
            zvm_run.extend(['-T', trace_log])
        zvm_run.append(manifest_file)
        runner = ZvRunner(zvm_run, self.zvsh.stdout, self.zvsh.stderr,
                          self.zvsh.tmpdir,
                          getrc=self.args.zvm_getrc)
        try:
            runner.run()
        finally:
            self.zvsh.cleanup()

    def _run_gdb(self):
        # user wants to debug the program
        zvsh_args = DebugArgs()
        zvsh_args.parse(self.cmd_line[1:])
        self.args = zvsh_args.args
        self.zvsh = ZvShell(self.config, self.args.zvm_save_dir)
        # a month until debug session will time out
        self.zvsh.config['manifest']['Timeout'] = 60 * 60 * 24 * 30
        manifest_file = self.zvsh.add_arguments(self.args)
        zvm_run = [DEBUG_EXECUTABLE, DEBUG_OPTIONS,
                   manifest_file]
        command_line = [GDB,
                        '--command=%s' % self.zvsh.add_debug_script()]
        command_line.extend(self.args.gdb_args)
        command_line.append('--args')
        command_line.extend(zvm_run)
        print (' '.join(command_line))
        try:
            spawn(command_line)
        except (KeyboardInterrupt, Exception):
            pass
        finally:
            self.zvsh.cleanup()

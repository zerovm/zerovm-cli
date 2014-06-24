import os
from tempfile import mkstemp, mkdtemp
import unittest
import errno
from shutil import rmtree
import sys
import pytest
import zvshlib
from zvshlib.zvsh import Shell, DEFAULT_LIMITS
from os.path import join as join_path

MULTIVAL = ['channel']
ZVSH = 'zvsh'

zvshlib.zvsh.ZEROVM_EXECUTABLE = 'false'
zvshlib.zvsh.ZEROVM_OPTIONS = ''


def mock_cleanup(self):
    pass

zvshlib.zvsh.ZvShell.orig_cleanup = zvshlib.zvsh.ZvShell.cleanup
zvshlib.zvsh.ZvShell.cleanup = mock_cleanup


def mock_return_code(report):
    return 0

zvshlib.zvsh.parse_return_code = mock_return_code


def mkdirs(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError as err:
            if err.errno != errno.EEXIST or not os.path.isdir(path):
                raise

sys.stderr = sys.stdout


class TestZvsh(unittest.TestCase):

    def setUp(self):
        self.program = 'text.nexe'
        self.argv = [ZVSH, self.program]
        self.maxDiff = None
        self.testdir = \
            os.path.join(mkdtemp(), 'zvsh')
        mkdirs(self.testdir)

    def tearDown(self):
        rmtree(os.path.dirname(self.testdir))

    def _reference_manifest(self, tmpdir, limits=None, executable=None):
        if not executable:
            executable = self.program
        if not limits:
            limits = DEFAULT_LIMITS
        reference = {
            'node': '1',
            'version': '20130611',
            'program': os.path.abspath(executable),
            'timeout': '50',
            'memory': [
                '4294967296',
                '0'
            ],
            'channel': [
                [
                    '/dev/stdin',
                    '/dev/stdin',
                    '0',
                    '0',
                    str(limits['reads']),
                    str(limits['rbytes']),
                    '0',
                    '0'
                ],
                [
                    join_path(tmpdir, 'stdout.1'),
                    '/dev/stdout',
                    '0',
                    '0',
                    '0',
                    '0',
                    str(limits['writes']),
                    str(limits['wbytes'])
                ],
                [
                    join_path(tmpdir, 'stderr.1'),
                    '/dev/stderr',
                    '0',
                    '0',
                    '0',
                    '0',
                    str(limits['writes']),
                    str(limits['wbytes'])
                ],
                [
                    os.path.abspath(executable),
                    '/dev/self',
                    '3',
                    '0',
                    str(limits['reads']),
                    str(limits['rbytes']),
                    '0',
                    '0'
                ],
                [
                    join_path(tmpdir, 'nvram.1'),
                    '/dev/nvram',
                    '3',
                    '0',
                    str(limits['reads']),
                    str(limits['rbytes']),
                    str(limits['writes']),
                    str(limits['wbytes'])
                ]
            ]
        }
        return reference

    def test_one_command(self):
        cmd_line = self.program
        shell = Shell(self.argv)
        try:
            with pytest.raises(SystemExit):
                shell.run()
            files = os.listdir(shell.zvsh.tmpdir)
            self.assertTrue('manifest.1' in files)
            self.assertTrue('nvram.1' in files)
            manifest = _read_manifest(join_path(shell.zvsh.tmpdir,
                                                'manifest.1'))
            reference = self._reference_manifest(shell.zvsh.tmpdir)
            self.assertEqual(manifest, reference)
            nvram = _read_nvram(join_path(shell.zvsh.tmpdir,
                                          'nvram.1'))
            reference = _reference_nvram(cmd_line)
            self.assertEqual(nvram, reference)
        finally:
            shell.zvsh.orig_cleanup()

    def test_command_with_args(self):
        opts = '-t --test test'
        cmd_line = ' '.join([self.program, opts])
        self.argv.extend(opts.split())
        shell = Shell(self.argv)
        try:
            with pytest.raises(SystemExit):
                shell.run()
            files = os.listdir(shell.zvsh.tmpdir)
            self.assertTrue('manifest.1' in files)
            self.assertTrue('nvram.1' in files)
            manifest = _read_manifest(join_path(shell.zvsh.tmpdir,
                                                'manifest.1'))
            reference = self._reference_manifest(shell.zvsh.tmpdir)
            self.assertEqual(manifest, reference)
            nvram = _read_nvram(join_path(shell.zvsh.tmpdir,
                                          'nvram.1'))
            reference = _reference_nvram(cmd_line)
            self.assertEqual(nvram, reference)
        finally:
            shell.zvsh.orig_cleanup()

    def test_existing_file(self):
        fd, name = mkstemp(dir=self.testdir)
        os.write(fd, b'test')
        os.close(fd)
        opts = '-f @%s' % name
        dev_name = '/dev/1.%s' % os.path.basename(name)
        cmd_line = ' '.join([self.program, '-f %s' % dev_name])
        self.argv.extend(opts.split())
        shell = Shell(self.argv)
        try:
            with pytest.raises(SystemExit):
                shell.run()
            files = os.listdir(shell.zvsh.tmpdir)
            self.assertTrue('manifest.1' in files)
            self.assertTrue('nvram.1' in files)
            manifest = _read_manifest(join_path(shell.zvsh.tmpdir,
                                                'manifest.1'))
            reference = self._reference_manifest(shell.zvsh.tmpdir)
            channels = reference['channel']
            file_chan = [name,
                         dev_name,
                         '3',
                         '0',
                         str(DEFAULT_LIMITS['reads']),
                         str(DEFAULT_LIMITS['rbytes']),
                         str(DEFAULT_LIMITS['writes']),
                         str(DEFAULT_LIMITS['wbytes'])]
            channels.insert(3, file_chan)
            self.assertEqual(manifest, reference)
            nvram = _read_nvram(join_path(shell.zvsh.tmpdir,
                                          'nvram.1'))
            reference = _reference_nvram(cmd_line,
                                         [{'channel': dev_name,
                                           'mode': 'file'}])
            self.assertEqual(nvram, reference)
        finally:
            shell.zvsh.orig_cleanup()

    def test_create_file(self):
        fd, name = mkstemp(dir=self.testdir)
        os.close(fd)
        os.unlink(name)
        self.assertFalse(os.path.exists(name))
        opts = '-f @%s' % name
        dev_name = '/dev/1.%s' % os.path.basename(name)
        cmd_line = ' '.join([self.program, '-f %s' % dev_name])
        self.argv.extend(opts.split())
        shell = Shell(self.argv)
        try:
            with pytest.raises(SystemExit):
                shell.run()
            files = os.listdir(shell.zvsh.tmpdir)
            self.assertTrue('manifest.1' in files)
            self.assertTrue('nvram.1' in files)
            manifest = _read_manifest(join_path(shell.zvsh.tmpdir,
                                                'manifest.1'))
            reference = self._reference_manifest(shell.zvsh.tmpdir)
            channels = reference['channel']
            file_chan = [name,
                         dev_name,
                         '3',
                         '0',
                         str(DEFAULT_LIMITS['reads']),
                         str(DEFAULT_LIMITS['rbytes']),
                         str(DEFAULT_LIMITS['writes']),
                         str(DEFAULT_LIMITS['wbytes'])]
            channels.insert(3, file_chan)
            self.assertEqual(manifest, reference)
            nvram = _read_nvram(join_path(shell.zvsh.tmpdir,
                                          'nvram.1'))
            reference = _reference_nvram(cmd_line,
                                         [{'channel': dev_name,
                                           'mode': 'file'}])
            self.assertEqual(nvram, reference)
            self.assertTrue(os.path.exists(name))
        finally:
            shell.zvsh.orig_cleanup()

    def test_input_output_file(self):
        in_fd, in_name = mkstemp(dir=self.testdir)
        os.write(in_fd, b'test')
        os.close(in_fd)
        out_fd, out_name = mkstemp(dir=self.testdir)
        os.close(out_fd)
        os.unlink(out_name)
        self.assertFalse(os.path.exists(out_name))
        opts = '-i @%s -o @%s' % (in_name, out_name)
        in_dev_name = '/dev/1.%s' % os.path.basename(in_name)
        out_dev_name = '/dev/2.%s' % os.path.basename(out_name)
        cmd_line = ' '.join([self.program, '-i %s -o %s'
                                           % (in_dev_name, out_dev_name)])
        self.argv.extend(opts.split())
        shell = Shell(self.argv)
        try:
            with pytest.raises(SystemExit):
                shell.run()
            files = os.listdir(shell.zvsh.tmpdir)
            self.assertTrue('manifest.1' in files)
            self.assertTrue('nvram.1' in files)
            manifest = _read_manifest(join_path(shell.zvsh.tmpdir,
                                                'manifest.1'))
            reference = self._reference_manifest(shell.zvsh.tmpdir)
            channels = reference['channel']
            file_chan = [out_name,
                         out_dev_name,
                         '3',
                         '0',
                         str(DEFAULT_LIMITS['reads']),
                         str(DEFAULT_LIMITS['rbytes']),
                         str(DEFAULT_LIMITS['writes']),
                         str(DEFAULT_LIMITS['wbytes'])]
            channels.insert(3, file_chan)
            file_chan = [in_name,
                         in_dev_name,
                         '3',
                         '0',
                         str(DEFAULT_LIMITS['reads']),
                         str(DEFAULT_LIMITS['rbytes']),
                         str(DEFAULT_LIMITS['writes']),
                         str(DEFAULT_LIMITS['wbytes'])]
            channels.insert(3, file_chan)
            self.assertEqual(manifest, reference)
            nvram = _read_nvram(join_path(shell.zvsh.tmpdir,
                                          'nvram.1'))
            reference = _reference_nvram(cmd_line,
                                         [{'channel': in_dev_name,
                                           'mode': 'file'},
                                          {'channel': out_dev_name,
                                           'mode': 'file'}])
            self.assertEqual(nvram, reference)
            self.assertTrue(os.path.exists(out_name))
        finally:
            shell.zvsh.orig_cleanup()


def _read_manifest(file_name):
    with open(file_name) as manifest:
        result = dict()
        lines = manifest.readlines()
        for l in [l.strip() for l in lines
                  if l.strip() and not l.startswith('==')]:
            k, v = [s.strip() for s in l.split('=', 1)]
            values = [s.strip() for s in v.split(',')]
            if len(values) == 1:
                values = values[0]
            k = k.lower()
            if k in MULTIVAL:
                result.setdefault(k, [])
                result[k].append(values)
            else:
                result[k] = values
        return result


def save_section(result, section, value):
    if section:
        if len(value) == 1:
            result[section] = value[0]
        else:
            result[section] = value[:]
        value = []
    return value


def _read_nvram(file_name):
    with open(file_name) as nvram:
        result = dict()
        lines = nvram.readlines()
        section = None
        value = []
        for l in [l.strip() for l in lines
                  if l.strip() and not l.startswith('#')]:
            if l.startswith('['):
                value = save_section(result, section, value)
                section = l.lstrip('[').rstrip(']')
                continue
            d = dict()
            for val in [s.strip() for s in l.split(',')]:
                k, v = [s.strip() for s in val.split('=', 1)]
                d[k] = v
            result.setdefault(section, [])
            value.append(d)
        save_section(result, section, value)
        return result


def _reference_nvram(command_line, additional_channels=None):
    reference = {
        'args': {
            'args': command_line
        },
        'mapping': []
    }
    if sys.stdin.isatty():
        reference['mapping'].append({
            'mode': 'char',
            'channel': '/dev/stdin'
        })
    if sys.stdout.isatty():
        reference['mapping'].append({
            'mode': 'char',
            'channel': '/dev/stdout'
        })
    if sys.stderr.isatty():
        reference['mapping'].append({
            'mode': 'char',
            'channel': '/dev/stderr'
        })
    if additional_channels:
        for chan in additional_channels:
            reference['mapping'].append(chan)
    if len(reference['mapping']) == 1:
        reference['mapping'] = reference['mapping'][0]
    elif len(reference['mapping']) == 0:
        del reference['mapping']
    return reference

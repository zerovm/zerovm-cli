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

import pytest

from zvshlib import zvsh


class TestChannel:
    """
    Tests for :class:`zvshlib.zvsh.Channel`.
    """

    def test_read_channel_with_defaults(self):
        # Simple string representation for a typical stdin read channel.
        chan = zvsh.Channel(
            '/dev/stdin',
            '/dev/stdin',
            0,
            puts=0,
            put_size=0,
        )
        exp = ('Channel = '
               '/dev/stdin,/dev/stdin,0,0,4294967296,4294967296,0,0')
        assert exp == str(chan)

    def test_read_channel(self):
        chan = zvsh.Channel(
            '/dev/stdin',
            '/dev/stdin',
            0,
            gets=1024,
            get_size=2048,
            puts=0,
            put_size=0,
        )
        exp = ('Channel = '
               '/dev/stdin,/dev/stdin,0,0,1024,2048,0,0')
        assert exp == str(chan)

    def test_write_channel_with_defaults(self):
        # Typical representation for a stdout write channel.
        # Uses defaults wherever possible.
        chan = zvsh.Channel(
            '/tmp/zvsh/stdout.1',
            '/dev/stdout',
            0,
            0,
            gets=0,
            get_size=0,
        )
        exp = ('Channel = '
               '/tmp/zvsh/stdout.1,/dev/stdout,0,0,0,0,4294967296,4294967296')
        assert exp == str(chan)

    def test_write_channel(self):
        chan = zvsh.Channel(
            '/tmp/zvsh/stdout.1',
            '/dev/stdout',
            0,
            0,
            gets=0,
            get_size=0,
            puts=256,
            put_size=128,
        )
        exp = ('Channel = '
               '/tmp/zvsh/stdout.1,/dev/stdout,0,0,0,0,256,128')
        assert exp == str(chan)

    def test_repr(self):
        chan = zvsh.Channel(
            '/dev/stdin',
            '/dev/stdin',
            0,
            puts=0,
            put_size=0,
        )
        exp = ('<Channel = '
               '/dev/stdin,/dev/stdin,0,0,4294967296,4294967296,0,0>')
        assert exp == repr(chan)


class TestManifest:
    """
    Tests for :class:`zvshlib.zvsh.Manifest`.
    """

    def test_default_manifest(self):
        io_lim = 4294967296
        expected = """\
Node = 1
Version = 20130611
Timeout = 50
Memory = 4294967296,0
Program = /tmp/zvsh/boot.1
Channel = /dev/stdin,/dev/stdin,0,0,%(io_lim)s,%(io_lim)s,0,0
Channel = /tmp/zvsh/stdout.1,/dev/stdout,0,0,0,0,%(io_lim)s,%(io_lim)s
Channel = /tmp/zvsh/stderr.1,/dev/stderr,0,0,0,0,%(io_lim)s,%(io_lim)s
Channel = /tmp/zvsh/nvram.1,/dev/nvram,3,0,%(io_lim)s,%(io_lim)s,%(io_lim)s,\
%(io_lim)s"""
        expected %= dict(io_lim=io_lim)

        man = zvsh.Manifest.default_manifest('/tmp/zvsh', '/tmp/zvsh/boot.1')
        assert expected == man.dumps()

    def test_default_manifest_with_custom_channel(self):
        io_lim = 4294967296
        expected = """\
Node = 1
Version = 20130611
Timeout = 50
Memory = 4294967296,0
Program = /tmp/zvsh/boot.1
Channel = /dev/stdin,/dev/stdin,0,0,%(lim)s,%(lim)s,0,0
Channel = /tmp/zvsh/stdout.1,/dev/stdout,0,0,0,0,%(lim)s,%(lim)s
Channel = /tmp/zvsh/stderr.1,/dev/stderr,0,0,0,0,%(lim)s,%(lim)s
Channel = \
/tmp/zvsh/nvram.1,/dev/nvram,3,0,%(lim)s,%(lim)s,%(lim)s,%(lim)s
Channel = \
/path/to/python.tar,/dev/5.python.tar,3,0,%(lim)s,%(lim)s,%(lim)s,%(lim)s"""
        expected %= dict(lim=io_lim)

        man = zvsh.Manifest.default_manifest('/tmp/zvsh', '/tmp/zvsh/boot.1')
        python_chan = zvsh.Channel(
            '/path/to/python.tar',
            '/dev/5.python.tar',
            zvsh.RND_READ_RND_WRITE,
        )
        man.channels.append(python_chan)
        assert expected == man.dumps()

    def test_manifest(self):
        # Generate a minimal manifest, with just 1 channel.
        io_lim = 2048
        expected = """\
Node = 1
Version = 20130611
Timeout = 10
Memory = 1024,0
Program = /tmp/zvsh/boot.1
Channel = \
/path/to/foo.tar,/dev/foo.tar,3,0,%(lim)s,%(lim)s,%(lim)s,%(lim)s"""
        expected %= dict(lim=io_lim)
        chan = zvsh.Channel('/path/to/foo.tar', '/dev/foo.tar',
                            zvsh.RND_READ_RND_WRITE, gets=2048, get_size=2048,
                            puts=2048, put_size=2048)
        man = zvsh.Manifest('20130611', 10, 1024, '/tmp/zvsh/boot.1',
                            channels=[chan])
        assert expected == man.dumps()

    def test_manifest_no_channels(self):
        # If there are no channels, an error should be raised.
        man = zvsh.Manifest('20130611', 10, 1024, '/tmp/zvsh.boot.1')
        with pytest.raises(RuntimeError):
            man.dumps()

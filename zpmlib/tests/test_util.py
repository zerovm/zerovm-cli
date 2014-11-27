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
import tempfile

import pytest

from zpmlib import util


class TestAtomicFileCreator:
    """Tests for :class:`zpmlib.util.AtomicFileCreator`.
    """

    def test_create_one_file(self):
        pass

    def test_create_one_dir(self):
        pass

    def test_create_multiple(self):
        # Create multiple files/dirs.
        pass

    def test_already_exists_rollback_file(self):
        # Test the rollback feature by attempting to create two files, the
        # second of which already exists.
        # Test that the first file gets deleted on the rollback.
        tempdir = tempfile.mkdtemp()
        try:
            file_one = os.path.join(tempdir, 'one.txt')
            file_two = os.path.join(tempdir, 'two.txt')
            # Create the file_two to cause the error
            open(file_two, 'w').close()

            afc = util.AtomicFileCreator()
            afc.create_file('file', file_one, 'abc')
            try:
                afc.create_file('file', file_two, 'def')
            except IOError:
                assert os.path.exists(file_one)
                assert not os.path.isdir(file_one)
                afc._rollback()
                # Make sure rollback deletes it
                assert not os.path.exists(file_one)
                # file_two was created before, and it should still exist
                assert os.path.exists(file_two)
            else:
                # No IOError, fail the test
                assert False, "Expected IOError not raised"
        finally:
            shutil.rmtree(tempdir)

    def test_already_exists_rollback_dir(self):
        # Test the rollback feature by attempting to create a dir and a file,
        # the second of which already exists.
        # Test that the dir gets deleted on the rollback.
        tempdir = tempfile.mkdtemp()
        try:
            dir_one = os.path.join(tempdir, 'dir_one')
            file_two = os.path.join(tempdir, 'two.txt')
            # Create the file_two to cause the error
            open(file_two, 'w').close()

            afc = util.AtomicFileCreator()
            afc.create_file('dir', dir_one, None)
            try:
                afc.create_file('file', file_two, 'def')
            except IOError:
                assert os.path.exists(dir_one)
                assert os.path.isdir(dir_one)
                afc._rollback()
                # Make sure rollback deletes it
                assert not os.path.exists(dir_one)
                # file_two was created before, and it should still exist
                assert os.path.exists(file_two)
            else:
                # No IOError, fail the test
                assert False, "Expected IOError not raised"
        finally:
            shutil.rmtree(tempdir)

    def test_context_manager_success_case(self):
        tempdir = tempfile.mkdtemp()
        try:
            dir_one = os.path.join(tempdir, 'dir_one')
            # This tests creating files inside created dirs:
            file_one = os.path.join(dir_one, 'one.txt')

            file_two = os.path.join(tempdir, 'two.txt')
            file_three = os.path.join(tempdir, 'three.txt')

            with util.AtomicFileCreator() as afc:
                afc.create_file('dir', dir_one, None)
                afc.create_file('file', file_one, 'abc')
                afc.create_file('file', file_two, 'def')
                afc.create_file('file', file_three, 'ghi')
            assert os.path.exists(dir_one)
            assert os.path.exists(file_one)
            with open(file_one) as fp:
                assert fp.read() == 'abc'
            assert os.path.exists(file_two)
            with open(file_two) as fp:
                assert fp.read() == 'def'
            assert os.path.exists(file_three)
            with open(file_three) as fp:
                assert fp.read() == 'ghi'
        finally:
            shutil.rmtree(tempdir)

    def test_context_manager_failure_case(self):
        tempdir = tempfile.mkdtemp()
        try:
            dir_one = os.path.join(tempdir, 'dir_one')
            # This tests creating files inside created dirs:
            file_one = os.path.join(dir_one, 'one.txt')

            file_two = os.path.join(tempdir, 'two.txt')
            file_three = os.path.join(tempdir, 'three.txt')

            # file_two will be pre-existing
            open(file_two, 'w').close()

            try:
                with util.AtomicFileCreator() as afc:
                    afc.create_file('dir', dir_one, None)
                    afc.create_file('file', file_one, 'abc')
                    afc.create_file('file', file_two, 'def')
                    afc.create_file('file', file_three, 'ghi')
            except IOError:
                assert afc._files_created == [
                    ('dir', dir_one, None),
                    ('file', file_one, 'abc'),
                ]
                # Test that everything was rolled back, except for the
                # pre-existing file.
                assert not os.path.exists(dir_one)
                assert not os.path.exists(file_one)
                assert os.path.exists(file_two)
                assert not os.path.exists(file_three)
            else:
                # No IOError, fail the test
                assert False, "Expected IOError not raised"
        finally:
            shutil.rmtree(tempdir)

    def test_invalid_file_type(self):
        afc = util.AtomicFileCreator()
        with pytest.raises(ValueError):
            afc.create_file('not_a_file', 'fake/path', 'abc')

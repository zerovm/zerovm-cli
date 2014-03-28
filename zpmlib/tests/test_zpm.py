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

import json
import mock
import os
import pytest
import shutil
import tempfile

from zpmlib import zpm


class TestCreateProject:
    """
    Tests for :func:`zpmlib.zpm.create_project`.
    """

    def test_path_exists_not_dir(self):
        # A RuntimeError should be thrown if the target path exists and is
        # not a dir.
        _, tf = tempfile.mkstemp()
        with mock.patch('zpmlib.zpm._create_zar_json') as czj:
            with pytest.raises(RuntimeError):
                zpm.create_project(tf)
            assert czj.call_count == 0

    def test_path_does_not_exist(self):
        # If the path does not exist, `create_project` should create the
        # directory (including intermediate directories) and bootstrap an empty
        # project.
        tempdir = tempfile.mkdtemp()
        target_dir = os.path.join(tempdir, 'foo', 'bar')

        try:
            with mock.patch('zpmlib.zpm._create_zar_json') as czj:
                zpm.create_project(target_dir)
                assert czj.call_count == 1
        finally:
            shutil.rmtree(tempdir)

    def test_target_is_dir(self):
        # In this case, the target is a dir and it exists already.
        tempdir = tempfile.mkdtemp()
        try:
            with mock.patch('zpmlib.zpm._create_zar_json') as czj:
                zpm.create_project(tempdir)
                assert czj.call_count == 1
        finally:
            shutil.rmtree(tempdir)


class TestCreateZarJSON:
    """
    Tests for :func:`zpmlib.zpm._create_zar_json`.
    """

    def test_file_already_exists(self):
        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'zar.json')
        # "touch" the file
        open(filepath, 'w').close()
        try:
            with pytest.raises(RuntimeError):
                zpm._create_zar_json(tempdir)
        finally:
            shutil.rmtree(tempdir)

    def test_create_zar_json(self):
        # Test the creation of zar.json.
        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'zar.json')

        try:
            assert not os.path.exists(filepath)
            zarjson = zpm._create_zar_json(tempdir)
            assert os.path.exists(filepath)
            with open(filepath) as fp:
                assert zpm.DEFAULT_ZAR_JSON == json.load(fp)
            assert os.path.abspath(filepath) == os.path.abspath(zarjson)
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
        zar = {'ui': ['x']}
        tar = mock.Mock(getnames=lambda: ['x', 'y'])
        matches = zpm._find_ui_uploads(zar, tar)
        assert sorted(matches) == ['x']

    def test_with_glob(self):
        zar = {'ui': ['x', 'ui/*']}
        tar = mock.Mock(getnames=lambda: ['x', 'y', 'ui/x', 'ui/y'])
        matches = zpm._find_ui_uploads(zar, tar)
        assert sorted(matches) == ['ui/x', 'ui/y', 'x']

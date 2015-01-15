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

from zpmlib import zapptemplate


class TestPythonTemplate:

    def test_without_ui(self):
        tempdir = tempfile.mkdtemp()

        try:
            files = list(zapptemplate.template(tempdir, 'python', False))

            proj_name = os.path.basename(os.path.abspath(tempdir))
            expected_zapp_yaml = zapptemplate.render_zapp_yaml(
                proj_name, template_name=zapptemplate._PYTHON_ZAPP_YAML
            )
            expected_files = [
                ('file', os.path.join(tempdir, 'zapp.yaml'),
                 expected_zapp_yaml),
                ('dir', os.path.join(tempdir, '.zapp'), None),
                ('file', os.path.join(tempdir, '.zapp', 'tox.ini'),
                 zapptemplate._PYTHON_TOX_INI_TEMPLATE),
            ]
            assert files == expected_files
        finally:
            shutil.rmtree(tempdir)

    def test_with_ui(self):
        tempdir = tempfile.mkdtemp()

        try:
            files = list(zapptemplate.template(tempdir, 'python', True))

            proj_name = os.path.basename(os.path.abspath(tempdir))
            expected_zapp_yaml = zapptemplate.render_zapp_yaml(
                proj_name, template_name=zapptemplate._PYTHON_ZAPP_WITH_UI_YAML
            )
            expected_index_html = open(
                os.path.join(zapptemplate.TEMPLATE_DIR,
                             'index.html.tmpl')).read()
            expected_style_css = open(
                os.path.join(zapptemplate.TEMPLATE_DIR,
                             'style.css')).read()
            expected_zerocloud_js = open(
                os.path.join(zapptemplate.TEMPLATE_DIR,
                             'zerocloud.js')).read()

            expected_files = [
                ('file', os.path.join(tempdir, 'zapp.yaml'),
                 expected_zapp_yaml),
                ('file', os.path.join(tempdir, 'index.html.tmpl'),
                 expected_index_html),
                ('file', os.path.join(tempdir, 'style.css'),
                 expected_style_css),
                ('file', os.path.join(tempdir, 'zerocloud.js'),
                 expected_zerocloud_js),
                ('dir', os.path.join(tempdir, '.zapp'), None),
                ('file', os.path.join(tempdir, '.zapp', 'tox.ini'),
                 zapptemplate._PYTHON_TOX_INI_TEMPLATE),
            ]
            assert files == expected_files
        finally:
            shutil.rmtree(tempdir)

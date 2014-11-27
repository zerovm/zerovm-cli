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
"""Template functions should accept a directory ``location`` and optional
``with_ui`` arguments.

Return values should be a iterator 3-tuples: (type, file_name, contents), where
`type` is 'dir' or 'file', `file_name` is the path to the file or dir, and
`contents` is the content of the file to be written (or ``None`` in the case
of a 'dir').
"""


import os
import jinja2

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
_DEFAULT_UI_TEMPLATES = ['index.html.tmpl', 'style.css', 'zerocloud.js']
_PYTHON_ZAPP_YAML = 'python-zapp.yaml'
_PYTHON_ZAPP_WITH_UI_YAML = 'python-zapp-with-ui.yaml'
_PYTHON_TOX_INI_TEMPLATE = """\
[tox]
toxworkdir={toxinidir}/.zapp
envlist = venv
skipsdist = true

[testenv:venv]
deps = -r{toxinidir}/deps.txt
"""


_DEFAULT_TEMPLATE = 'python'


def template(location, template, with_ui):
    return _TEMPLATES.get(template, _DEFAULT_TEMPLATE)(
        location, with_ui=with_ui
    )


def render_zapp_yaml(name, template_name=_PYTHON_ZAPP_YAML):
    # TODO: wtf is `name`?
    """Load and render the zapp.yaml template."""
    loader = jinja2.PackageLoader('zpmlib', 'templates')
    env = jinja2.Environment(loader=loader)
    tmpl = env.get_template(template_name)
    return tmpl.render(name=name)


def _create_basic_proj_files(location, with_ui=False):
    """Create common project files: zapp.yaml and basic HTML/JavaScript UI
    files (if ``with_ui`` is `True`).
    """
    # Add zapp.yaml template
    if with_ui:
        zapp_template = _PYTHON_ZAPP_WITH_UI_YAML
    else:
        zapp_template = _PYTHON_ZAPP_YAML

    # Start yielding project file tuples
    name = os.path.basename(os.path.abspath(location))
    yield ('file', os.path.join(location, 'zapp.yaml'),
           render_zapp_yaml(name, template_name=zapp_template))

    # Add UI template files, if specified
    if with_ui:
        for template in _DEFAULT_UI_TEMPLATES:
            src_path = os.path.join(TEMPLATE_DIR, template)
            dest_path = os.path.join(location, template)

            with open(src_path) as fp:
                yield ('file', dest_path, fp.read())


def python_template(location, with_ui=False):
    for triple in _create_basic_proj_files(location, with_ui=with_ui):
        yield triple

    dot_zapp_dir = os.path.join(location, '.zapp')
    yield ('dir', dot_zapp_dir, None)

    tox_ini_path = os.path.join(dot_zapp_dir, 'tox.ini')

    yield ('file', tox_ini_path, _PYTHON_TOX_INI_TEMPLATE)


_TEMPLATES = {
    'python': python_template,
}

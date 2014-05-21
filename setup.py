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

"""
ZeroVM Package Manager
"""

from distutils.core import setup

import zpmlib

setup(
    name='zpm',
    version=zpmlib.__version__,
    maintainer='Rackspace ZeroVM Team',
    maintainer_email='zerovm@rackspace.com',
    url='https://github.com/zerovm/zpm',
    description='ZeroVM Package Manager',
    long_description=open('README.rst').read(),
    platforms=['any'],
    packages=['zpmlib'],
    package_data={'zpmlib': ['templates/*.html', 'templates/*.css',
                             'templates/*.js', 'templates/*.yaml']},
    provides=['zpm (%s)' % zpmlib.__version__],
    install_requires=['requests', 'jinja2<2.7', 'pyyaml'],
    license='Apache 2.0',
    keywords='zpm zerovm zvm',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Build Tools',
    ),
    scripts=['zpm'],
)

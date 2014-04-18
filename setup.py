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
ZeroVM Shell
"""

from setuptools import find_packages
from setuptools import setup

import sys

requires = []
if sys.version_info < (2, 7):
    requires.append('ordereddict')

VERSION = '0.9.4'

setup(
    name='zvsh',
    version=VERSION,
    maintainer='Rackspace ZeroVM Team',
    maintainer_email='zerovm@rackspace.com',
    url='https://github.com/zerovm/zerovm-cli',
    description='ZeroVM Shell',
    long_description=__doc__,
    platforms=['any'],
    packages=find_packages(exclude=['zvshlib.tests', 'zvshlib.tests.*']),
    provides=['zvsh (%s)' % VERSION],
    install_requires=requires,
    license='Apache 2.0',
    keywords='zvsh zerovm zvm',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Build Tools',
    ),
    scripts=['zvsh'],
)

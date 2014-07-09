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

import sys

requires = []
if sys.version_info < (2, 7):
    requires.append('ordereddict')

kwargs = {}
try:
    from setuptools import setup
    kwargs['install_requires'] = requires
except ImportError:
    sys.stderr.write('warning: setuptools not found, you must '
                     'manually install dependencies!\n')
    from distutils.core import setup

import zvshlib


VERSION = zvshlib.__version__

setup(
    name='zvsh',
    version=VERSION,
    maintainer='Rackspace ZeroVM Team',
    maintainer_email='zerovm@rackspace.com',
    url='https://github.com/zerovm/zerovm-cli',
    description='ZeroVM Shell',
    long_description=__doc__,
    platforms=['any'],
    packages=['zvshlib'],
    provides=['zvsh (%s)' % VERSION],
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
    **kwargs
)

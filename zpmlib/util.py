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


class AtomicFileCreator(object):
    """Atomically create a group of files/directories, with a rollback function
    if any or all of the files exist, or if there is another problem.
    """

    def __init__(self):
        self._files_created = []

    def _rollback(self):
        for file_type, path, _contents in self._files_created:
            if file_type == 'file':
                if os.path.exists(path):
                    os.remove(path)
            elif file_type == 'dir':
                shutil.rmtree(path)

    def create_file(self, file_type, path, contents):
        """
        Create a file or directory.

        :param str file_type:
            "file" or "dir"
        :param str path:
            Path to the file or directory to be created.
        :param str contents:
            Contents of the file. Can be `None` (and is ignored) when
            ``file_type`` is "dir".
        """
        if os.path.exists(path):
            raise IOError("'%s' already exists!" % path)

        if file_type == 'file':
            with open(path, 'w') as fp:
                fp.write(contents)
        elif file_type == 'dir':
            os.makedirs(path)
        else:
            raise ValueError("Invalid file type '%s'!" % file_type)

        self._files_created.append((file_type, path, contents))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, _traceback):
        if exc_type is not None:
            self._rollback()
            raise exc_value

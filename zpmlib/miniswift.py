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
import requests

"""Small Swift client library."""


class SwiftClient(object):
    """
    Lightweight Swift client. Supports authentication to Keystone and basic
    Swift functions.

    :param auth_url:
        Keystone authorization URL, akin to `--os-auth-url` / `OS_AUTH_URL`.

        The URL against which we can perform Swift operations is retrieved from
        the Keystone service catalog, which is obtained when we authenticate to
        this `auth_url`.
    :param tenant:
        Keystone tenant name, akin to `--os-tenant-name` / `OS_TENANT_NAME`).
    :param username:
        Keystone username, akin to `--os-username` / `OS_USERNAME`.
    :param password:
        Keystone password, akin to `--os-password` / `OS_PASSWORD`.
    """

    def __init__(self, auth_url, tenant, username, password):
        self._auth_url = auth_url
        self._tenant = tenant
        self._username = username
        self._password = password

        self._token = None
        self._swift_service_url = None

    def auth(self):
        """
        Connect to the Keystone service and cache the access token and Swift
        endpoint URL (if available in the service catalog).

        Calling this is a prequisite for any Swift operations.
        """
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        payload = {'auth':
                   {'tenantName': self._tenant,
                    'passwordCredentials':
                    {'username': self._username, 'password': self._password}}}
        r = requests.post(self._auth_url + '/tokens',
                          data=json.dumps(payload),
                          headers=headers)
        data = r.json()

        self._token = data['access']['token']['id']
        print('found token: %s...' % self._token[:20])

        for service in data['access']['serviceCatalog']:
            if service['name'] == 'swift':
                self._swift_service_url = service['endpoints'][0]['publicURL']
                # Force hostname to be localhost -- for testing with a
                # SSH tunnel when Swift cannot be reached directly.
                # p = list(urlparse.urlparse(self._swift_url))
                # parts = list(p)
                # parts[1] = 'localhost:%d' % p.port
                # self._swift_url = urlparse.urlunparse(parts)
                print('found Swift: %s' % self._swift_service_url)

    def upload(self, path, data):
        """
        Upload file contents in `data` to the `path` in Swift.

        :param path:
            <container>/<filename> in Swift where we want to upload the given
            `data`.
        :param data:
            Contents of a file, as a string/bytes.
        """
        headers = {'X-Auth-Token': self._token}
        r = requests.put('%s/%s' % (self._swift_service_url, path),
                         data=data, headers=headers)
        if r.status_code == 200:
            print('created %s succesfully' % path)
        elif r.status_code == 201:
            print('updated %s succesfully' % path)
        else:
            raise RuntimeError('uploading %s failed with status %d'
                               % (path, r.status_code))


class ZwiftClient(SwiftClient):
    """
    Extends :class:`SwiftClient` to add ZeroVM/zar execution functionality.
    """

    def post_job(self, job):
        """
        Start a ZeroVM job, using a pre-uploaded zar.

        :param object job:
            Object that will be encoded as JSON sent to Zwift. For
            more information about the job/servlet configuration, see
            https://github.com/zerovm/zerocloud/blob/icehouse/doc/Servlets.md
        """
        headers = {'X-Auth-Token': self._token,
                   'Accept': 'application/json',
                   'X-Zerovm-Execute': '1.0',
                   'Content-Type': 'application/json'}
        json_data = json.dumps(job)
        r = requests.post(self._swift_service_url, data=json_data,
                          headers=headers)
        print(r)
        print(r.content)

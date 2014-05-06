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
import zpmlib

from zpmlib import LOG

"""Small Swift client library."""


class SwiftClient(object):
    """
    Lightweight Swift client. Supports authentication Keystone (v2 auth),
    authentication to Swift (v1 auth), and basic Swift functions.

    :param auth_url:
        Auth v1:
            Swift authorization URL, akin to ``--auth`` / ``ST_AUTH``.

        Auth v2:
            Keystone authorization URL, akin to ``--os-auth-url`` /
            ``OS_AUTH_URL``.

            The URL against which we can perform Swift operations is retrieved
            from the Keystone service catalog, which is obtained when we
            authenticate to this ``auth_url``.

        See also ``auth_version``.
    :param username:
        Auth v1:
            Swift username, akin to ``--user`` / ``ST_USER``.
        Auth v2:
            Keystone username, akin to ``--os-username`` / ``OS_USERNAME``.
    :param password:
        Auth v1:
            Swift key, akin to ``--key`` / ``ST_KEY``.
        Auth v2:
            Keystone password, akin to ``--os-password`` / ``OS_PASSWORD``.
    :param tenant:
        Only used if ``auth_version`` is 2 (not 1).

        Keystone tenant name, akin to ``--os-tenant-name`` /
        ``OS_TENANT_NAME``).
    :param int auth_version:
        Use auth version 1 or 2. Defaults to 1.
    """

    def __init__(self, auth_url, username, password, tenant=None,
                 auth_version=1):
        self._auth_url = auth_url
        self._username = username
        self._password = password
        self._auth_version = auth_version

        self._tenant = tenant

        self._token = None
        self._swift_service_url = None

    def auth(self):
        """
        Connect to the authentication service and cache the access token and
        Swift endpoint URL.

        Calling this is a prequisite for any Swift operations.
        """
        if self._auth_version == 1:
            headers = {
                'X-Auth-User': self._username,
                'X-Auth-Key': self._password,
            }
            r = requests.get(self._auth_url, headers=headers)
            self._token = r.headers['x-auth-token']
            self._swift_service_url = r.headers['x-storage-url']
        elif self._auth_version == 2:
            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}
            payload = {'auth':
                       {'tenantName': self._tenant,
                        'passwordCredentials':
                        {'username': self._username,
                         'password': self._password}}}
            r = requests.post(self._auth_url + '/tokens',
                              data=json.dumps(payload),
                              headers=headers)
            data = r.json()

            self._token = data['access']['token']['id']
            LOG.info('found token: %s...' % self._token[:20])

            for service in data['access']['serviceCatalog']:
                if service['name'] == 'swift':
                    self._swift_service_url = (
                        service['endpoints'][0]['publicURL']
                    )
                    # Force hostname to be localhost -- for testing with a
                    # SSH tunnel when Swift cannot be reached directly.
                    # p = list(urlparse.urlparse(self._swift_url))
                    # parts = list(p)
                    # parts[1] = 'localhost:%d' % p.port
                    # self._swift_url = urlparse.urlunparse(parts)
                    LOG.info('found Swift: %s' % self._swift_service_url)
                    break
            else:
                # No swift found; we can't really do anything without this.
                # This is a 'SwiftClient', afterall. =)
                raise zpmlib.ZPMException(
                    "'swift' was not found in the service catalog at '%s'"
                    % self._auth_url
                )
        else:
            raise zpmlib.ZPMException("Unsupported auth version '%s'"
                                      % self._auth_version)

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
            LOG.info('created %s succesfully' % path)
        elif r.status_code == 201:
            LOG.info('updated %s succesfully' % path)
        else:
            raise RuntimeError('uploading %s failed with status %d'
                               % (path, r.status_code))

    def download(self, container, filename):
        """
        Download ``filename`` from the given ``container``.

        :param container:
            Name of a Swift container.
        :param filename:
            Name of the file in the ``container`` to download.
        :returns:
            :class:`requests.models.Response` object.
        """
        headers = {'X-Auth-Token': self._token}
        url = '/'.join([self._swift_service_url, container, filename])
        resp = requests.get(url, headers=headers)
        return resp


class ZeroCloudClient(SwiftClient):
    """
    Extends :class:`SwiftClient` to add ZeroVM/zapp execution functionality.
    """

    def post_job(self, job):
        """
        Start a ZeroVM job, using a pre-uploaded zapp.

        :param object job:
            Object that will be encoded as JSON sent to ZeroCloud. For
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
        LOG.debug('response status: %s' % r.status_code)
        print(r.content)

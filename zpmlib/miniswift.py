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

    def __init__(self, auth_url, tenant, username, password):
        self._auth_url = auth_url
        self._tenant = tenant
        self._username = username
        self._password = password

        self._token = None
        self._swift_url = None

    def auth(self):
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
                self._swift_url = service['endpoints'][0]['publicURL']
                # Force hostname to be localhost -- for testing with a
                # SSH tunnel when Swift cannot be reached directly.
                # p = list(urlparse.urlparse(self._swift_url))
                # parts = list(p)
                # parts[1] = 'localhost:%d' % p.port
                # self._swift_url = urlparse.urlunparse(parts)
                print('found Swift: %s' % self._swift_url)

    def upload(self, path, data):
        print('uploading %d bytes to %s' % (len(data), path))
        headers = {'X-Auth-Token': self._token}
        r = requests.put('%s/%s' % (self._swift_url, path),
                         data=data, headers=headers)
        if r.status_code == 200:
            print('created %s succesfully' % path)
        elif r.status_code == 201:
            print('updated %s succesfully' % path)
        else:
            raise RuntimeError('uploading %s failed with status %d'
                               % (path, r.status_code))


class ZwiftClient(SwiftClient):

    def post_job(self, job):
        headers = {'X-Auth-Token': self._token,
                   'Accept': 'application/json',
                   'X-Zerovm-Execute': '1.0',
                   'Content-Type': 'application/json'}
        r = requests.post(self._swift_url, data=job, headers=headers)
        print(r)
        print(r.content)

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

import mock
import pytest
import zpmlib

from zpmlib import miniswift


class TestSwiftClient:
    """
    Tests for :class:`zpmlib.miniswift.SwiftClient`.
    """

    def setup_method(self, _method):
        self.tenant = dict(
            enabled=True,
            description=None,
            name='demo',
            id='469a9cd20b5a4fc5be9438f66bb5ee04',
        )
        self.token = dict(
            id='0123456789abcdef',
            issued_at='2014-03-26T19:20:09.156356',
            expires='2014-03-26T20:20:09Z',
            tenant=self.tenant,
        )
        self.swift_service_url = (
            'http://localhost:8080/v1/AUTH_3f748bc979db2b37bfc56ed5922cdebd'
        )
        self.service_catalog = [
            dict(
                endpoints_links=[],
                endpoints=[
                    dict(
                        id='968f382613384912aaf3a09980cab68a',
                        adminURL='http://localhost:8080',
                        region='regionOne',
                        publicURL=self.swift_service_url,
                        internalURL=self.swift_service_url,
                    )
                ],
                type='object-store',
                name='swift',
            ),
            dict(
                endpoints_links=[],
                endpoints=[
                    dict(
                        id='1f676fe679124b00967b0223d296294b',
                        adminURL='http://localhost:35357/v2.0',
                        region='RegionOne',
                        publicURL='http://localhost:5000/v2.0',
                        internalURL='http://localhost:5000/v2.0',
                    )
                ],
                type='identity',
                name='keystone',
            ),
        ]

        self.auth_url = 'http://localhost:5000/v2.0'
        self.tenant = 'demo'
        self.username = 'admin'
        self.password = 'admin-password'
        self.client = miniswift.SwiftClient(self.auth_url,
                                            self.username,
                                            self.password,
                                            tenant=self.tenant,
                                            auth_version=2)
        # mocked auth response data
        self.auth_resp_data = dict()
        self.auth_resp_data['access'] = dict(
            token=self.token,
            serviceCatalog=self.service_catalog,
        )

    def test_auth(self):
        # This is the basic auth case. By hitting a known auth url, we expect
        # to receive and cache two pieces of information:
        #  * token
        #  * swift url (from the service catalog)
        # The actual request to the auth url is mocked so we can focus on the
        # logic surrounding the response.
        with mock.patch('requests.post') as post:
            resp = mock.Mock()
            resp.json = lambda: self.auth_resp_data
            post.return_value = resp

            assert self.client._swift_service_url is None
            assert self.client._token is None
            self.client.auth()
            assert self.client._swift_service_url == self.swift_service_url
            assert self.client._token == self.token['id']

    def test_auth_no_swift_service(self):
        # Test what happens when there's no swift in the service catalog.
        # This is kind of crucial, so we expect an exception here if there's no
        # swift service.

        # remove swift from a the service catalog:
        self.service_catalog.pop(0)

        with mock.patch('requests.post') as post:
            resp = mock.Mock()
            resp.json = lambda: self.auth_resp_data
            post.return_value = resp

            assert self.client._swift_service_url is None
            assert self.client._token is None
            with pytest.raises(zpmlib.ZPMException):
                self.client.auth()

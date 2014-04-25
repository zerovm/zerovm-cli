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

    def _setup_auth_v1(self):
        self.v1_auth_url = 'http://example.com/auth/v1.0'
        self.user = 'test_tenant:test_user'
        self.key = '13dd08f4-ad7b-45ec-8f83-ce1d8a3b4796'
        self.v1_client = miniswift.SwiftClient(
            self.v1_auth_url,
            self.user,
            self.key
        )

    def _setup_auth_v2(self):
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

        self.username = 'admin'
        self.password = 'admin-password'

        self.v2_auth_url = 'http://localhost:5000/v2.0'
        self.v2_tenant = 'demo'
        self.v2_client = miniswift.SwiftClient(self.v2_auth_url,
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

    def test_auth_v1(self):
        # 1) Test that the correct parameters are passed to the v1 auth request
        # 2) Test that the swift url and auth token are cached correctly
        self._setup_auth_v1()

        exp_auth_token = 'AUTH_tk028ec863d0c5490db62b3bfc02b56336'
        exp_swift_url = (
            'http://example.com/v1/AUTH_81b8a52b-7fc7-4afa-bf01-acc41626498b'
        )
        exp_get_args = (
            (self.v1_auth_url, ),
            {'headers': {'X-Auth-User': self.user, 'X-Auth-Key': self.key}}
        )

        with mock.patch('requests.get') as get:
            resp = mock.Mock()
            resp.headers = {
                'x-storage-url': exp_swift_url,
                'x-auth-token': exp_auth_token,
            }
            get.return_value = resp

            self.v1_client.auth()
            assert get.call_args[0] == exp_get_args[0]  # pos args
            assert get.call_args[1] == exp_get_args[1]  # kwargs
            assert self.v1_client._swift_service_url == exp_swift_url
            assert self.v1_client._token == exp_auth_token

    def test_auth_v2(self):
        # This is the basic auth case. By hitting a known auth url, we expect
        # to receive and cache two pieces of information:
        #  * token
        #  * swift url (from the service catalog)
        # The actual request to the auth url is mocked so we can focus on the
        # logic surrounding the response.
        self._setup_auth_v2()

        with mock.patch('requests.post') as post:
            resp = mock.Mock()
            resp.json = lambda: self.auth_resp_data
            post.return_value = resp

            assert self.v2_client._swift_service_url is None
            assert self.v2_client._token is None
            self.v2_client.auth()
            assert self.v2_client._swift_service_url == self.swift_service_url
            assert self.v2_client._token == self.token['id']

    def test_auth_v2_no_swift_service(self):
        # Test what happens when there's no swift in the service catalog.
        # This is kind of crucial, so we expect an exception here if there's no
        # swift service.
        self._setup_auth_v2()

        # remove swift from a the service catalog:
        self.service_catalog.pop(0)

        with mock.patch('requests.post') as post:
            resp = mock.Mock()
            resp.json = lambda: self.auth_resp_data
            post.return_value = resp

            assert self.v2_client._swift_service_url is None
            assert self.v2_client._token is None
            with pytest.raises(zpmlib.ZPMException):
                self.v2_client.auth()

    def test_auth_unknown_version(self):
        with pytest.raises(zpmlib.ZPMException):
            client = miniswift.SwiftClient(
                'http://example.com:5000/v2.0',
                'admin',
                'admin-password',
                auth_version=3
            )
            client.auth()

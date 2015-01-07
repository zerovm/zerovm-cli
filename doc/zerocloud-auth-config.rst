ZeroCloud Authentication Config
===============================

`ZeroCloud <https://github.com/zerovm/zerocloud>`_ is middleware for
`OpenStack Swift <http://docs.openstack.org/developer/swift/>`_ which enables
ZeroVM applications to run on stored objects. :ref:`Deploying <zpm-deploy>`
applications to ZeroCloud using ``zpm`` requires authentication.

``zpm`` currently supports both v1 and v2 authentication schemes through the
use of command-line flags and environment variables. See below for instructions
and best practices for handling both versions.

Auth v1
-------

Authentication parameters can be specified directly on the command-line like
so::

    $ zpm deploy --auth http://example.com:5000/auth/v1.0 \
                 --user tenant1:user1 \
                 --key f0ec1500-de68-42bd-8350-f671b50a79bd \
                 test_container hello.zapp

Note that with v1, the ``--user`` is a concatentation of the tenant name and
the username, contrasted with v2 where they are specified separately. (See
below.)

You can also specify the authenication parameters by setting
the following environment variables::

    $ export ST_AUTH=http://example.com:5000/auth/v1.0
    $ export ST_USER=tenant1:user1
    $ export ST_KEY=f0ec1500-de68-42bd-8350-f671b50a79bd

Which shortens the ``zpm`` command to this::

    $ zpm deploy test_container hello.zapp

For convenience, you can put the above ``export`` statements into a text file
(called ``zerocloud_v1``, for example) and ``source`` it to automatically set
up your environment::

    $ source zerocloud_v1

Auth v2
-------

Authentication parameters can be specified directly on the command-line like
so::

    $ zpm deploy --os-auth-url http://example.com:5000/v2.0 \
                 --os-username user1 \
                 --os-tenant-name tenant1
                 --os-password secret \
                 test_container hello.zapp

``--os-auth-url`` should be the public endpoint defined for
`Keystone <http://docs.openstack.org/developer/keystone/>`_.

You can also specify the authenication parameters by setting
the following environment variables::

    $ export OS_AUTH_URL=http://example.com:5000/v2.0
    $ export OS_USERNAME=user1
    $ export OS_PASSWORD=secret
    $ export OS_TENANT_NAME=tenant1

Which shortens the ``zpm`` command to this::

    $ zpm deploy test_container hello.zapp

For convenience, you can put the above ``export`` statements into a text file
(called ``zerocloud_v2``, for example) and ``source`` it to automatically set
up your environment::

    $ source zerocloud_v2


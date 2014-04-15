
Introduction
============

The ZeroVM Package Manager, ZPM, is the tool you use to create and
deploy ZeroVM applications.


Creating a ZeroVM Application
-----------------------------

We will use a simple Python application as our running example.

.. note::

   As of version 0.1, ZPM only supports Python applications with no
   third-party dependencies.

To get started, we will show how to package a very simple "Hello
World" application. There will be just one file, ``hello.py``, with
the expected content::

   print "Hello from ZeroVM!"

To bundle this into a ZAR, ZPM needs a configuration file called
``zar.yaml``.

Configuration File
""""""""""""""""""

The ``zar.yaml`` file will look like this:

.. code-block:: yaml

   meta:
     Version: "0.1"
     name: hello
     Author-email: Martin Geisler <martin@geisler.net>
     Summary: A small Hello World app

   execution:
     groups:
       - name: hello
         path: file://python2.7:python
         args: /hello.py
         devices:
         - name: python2.7
         - name: stdout

   help:
     description: A small "Hello World" app.

   bundling:
     - hello.py

The file is in `YAML format <yaml_>`_ and describes the program to
execute, some meta data about it, help about the program and its
arguments (this program has none), and finally information about which
files to include when bundling. The different sections are described
in more detail in :ref:`zar-yaml`.


Bundling
""""""""

Simply running ``zpm bundle`` will create the ``hello.zar``::

   $ zpm bundle
   adding /home/mg/src/hello/hello.py
   adding /home/mg/src/hello/zar.yaml
   created hello.zar

You see the files added to the ZAR --- here it's simply ``hello.py``
together with the ``zar.yaml`` file containing the meta data.

You can now publish ``hello.zar`` on your webserver, send it to your
friends, etc. They will be able to run it after they deploy it like we
describe next.

Deployment
""""""""""

To deploy ``hello.zar``, you need access to a Zwift cluster (Swift
running the ZeroVM middleware). Like the ``swift`` command line client
for Swift, ``zpm`` will read your credentials from environemnt
variables if you don't pass them on the command line. The environment
variables are:

.. code-block:: sh

   export OS_TENANT_NAME=demo
   export OS_USERNAME=demo
   export OS_PASSWORD=pw
   export OS_AUTH_URL=http://localhost:5000/v2.0

We will deploy it to a ``test`` container under the folder
``hello``::

   $ zpm deploy hello.zar test/hello
   deploying hello.zar
   found token: MIIGjwYJKoZIhvcNAQcC...
   found Swift: http://localhost:8080/v1/account
   uploading 398 bytes to test/hello/hello.zar
   updated test/hello/hello.zar succesfully

For testing, you can execute the job after it has been deployed::

   $ zpm deploy hello.zar test/hello --execute
   deploying hello.zar
   found token: MIIGjwYJKoZIhvcNAQcC...
   found Swift: http://localhost:8080/v1/account
   uploading 398 bytes to test/hello/hello.zar
   updated test/hello/hello.zar succesfully
   job template:
   [{'exec': {'args': '/hello.py', 'path': u'file://python2.7:python'},
     'file_list': [{'device': u'python2.7'},
                   {'device': u'stdout'},
                   {'device': 'image',
                    'path': u'swift://account/test/hello/hello.zar'}],
     'name': u'hello'}]
   executing
   <Response [200]>
   Hello from ZeroVM!

There currently is no support for executing the application later. `Issue
#37 <issue37_>`_ deals with that.

.. _yaml: http://www.yaml.org/
.. _issue37: https://github.com/zerovm/zpm/issues/37

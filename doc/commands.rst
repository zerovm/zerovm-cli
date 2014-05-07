
ZPM Commands
============

The ``zpm`` script has the following top-level commands:


.. _zpm-new:

``zpm new``
-----------

.. autocommand:: zpmlib.commands.new

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: new


.. _zpm-deploy:


``zpm deploy``
--------------

.. autocommand:: zpmlib.commands.deploy

For help on configuring authentication, see
:doc:`zerocloud-auth-config`.

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: deploy


.. _zpm-bundle:

``zpm bundle``
--------------

.. autocommand:: zpmlib.commands.bundle

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: bundle


.. _zpm-execute:

``zpm execute``
---------------

.. autocommand:: zpmlib.commands.execute

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: execute


.. _zpm-help:

``zpm help``
------------

.. autocommand:: zpmlib.commands.help

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: help

``zpm version``
---------------

.. autocommand:: zpmlib.commands.version

.. argparse::
   :module: zpmlib.commands
   :func: set_up_arg_parser
   :prog: zpm
   :path: version

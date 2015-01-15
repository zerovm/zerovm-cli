
.. _zapp-yaml:

The ``zapp.yaml`` File
======================

The ``zapp.yaml`` plays a central role when writing an application for
deployment on ZeroCloud. This is where you specify things such as:

* Meta-data about the zapp, such as the name of the author and the
  version number.

* Where to find the NaCl executables ("nexes") and other files that
  make up the ZeroVM applicaiton. These are the files that ``zpm
  bundle`` include into the zapp.

* Arguments that must be specifed when the application is execution.
  These will be invocation specific.

A sample ``zapp.yaml`` file for a simple "Hello World" application
looks like this:

.. code-block:: yaml

   meta:
     Version: "0.1"
     name: hello
     Author-email: Your Name <your.name@example.net>
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
     description: Enter your name and you will be greeted
     args:
     - [name, Your name]

   bundling:
     - hello.py

The file is a simple YAML document. At the top, there is a mapping
with a number of keys which we will call "sections" in the following.
Each section describes part of the zapp file produced. We will go
throught the sections now.


The ``meta`` Section
--------------------

This section describes the generated zapp. The meta data here is
currently unused, but we expect it to be used for a future zapp
repository, i.e., a website where you can upload a zapp and let others
download it.

The keys in this section are:

``name``
  The short name of your zapp.

``summary``
  A short summary of what your zapp does.

``author-email``
  Your name and email.

``version``
  The version number of your zapp.


The ``execution`` Section
-------------------------

This section describes the runtime behavior of your zapp: which groups
of nodes to create and which :term:`nexe` to invoke for each. The
``groups`` key is a list of individual groups. Each group has these
keys:

``name``
  The name of this group. You use reference this name when you connect
  a group of nodes to another group.

``path``
  Path to the :term:`nexe` that all nodes in this group will execute.
  You will typically specify this as :file:`file://{image}:{nexe}`,
  which means that the nexe is found in the system image called
  ``image`` under the name ``nexe``. The path to the nexe is relative
  to the root of the system image.

``args``
  Command line arguments that will be passed to the :term:`nexe`.

``devices``
  List of devices that this group need. Each device has a ``name``
  which determines the type of device. These are the standard devices
  that are always present:

  ``stdin``
    This device feeds standard input to your program. You need to
    specify a ``path`` as well as ``name``. The ``path`` can be a
    ``swift://`` URL pointing to an object, which will make ZeroCloud
    execute the application on a Swift nodes that holds his object.

  ``stdout``
    This device captures the standard output of your program. If you
    don't specify a ``path``, the output is simply passed back to you
    when you invoke the program. This is how the default web UI shows
    the program output. If you do specify a ``swift://`` URL in
    ``path``, the output is stored there.

  ``stderr``
    This device captures the standard output of your program. You need
    to specify where the output should be stored using a ``swift://``
    URL in ``path``. Otherwise the error output will be discarded.

  In addition a ZeroCloud installation can offer a number of :term:`system
  images <system image>`. They will have to be installed by the system
  adminitrator of the system your users deploy the zapp onto.
  Referencing a system image will cause it to be mounted as the root
  filesystem when nexe is executed. These are the initially supported
  system images:

  ``python27``
    This gives you a Python 2.7 environment. The interpreter should be
    specified as ``file://python27:python`` in the ``path`` key.

``connect``

  List of other groups that this group should be connected with.
  Before the execution starts, devices will automatically be created
  to connect the nodes in the groups.

  If a group with *n* nodes named ``foo`` connects to a group with *m*
  nodes called ``bar``, then. Nodes in the ``foo`` group will find
  devices named::

    /dev/out/bar-1
    /dev/out/bar-2
    ...
    /dev/out/bar-m

  corresponding to each of the *m* instances in the ``bar`` group.
  Each of the *n* nodes in ``bar`` will find these devices::

    /dev/in/foo-1
    /dev/in/foo-2
    ...
    /dev/in/foo-n

  If there is only a single node in a group, the corresponding device
  is named `/dev/out/bar` or `/dev/in/foo`.

  What is written on channel in `/dev/out` appears on the
  corresponding channel in `/dev/in`.

``count``

  Defaults to 1. This can be used to specify the number of nodes in a
  group that would otherwise just have a single node, i.e., because
  the node writes to a single output object. The count is ignored if a
  device path contains a wildcard.

``replicate``

  Defaults to 1 which means no replication, other supported values are
  2 and 3. This will make ZeroCloud run multiple copies of the nodes
  in the group.

``attach``

  Override the strategy used by ZeroCloud to place nodes in the Swift
  cluster. By default, ZeroCloud will start jobs on the node holding
  the input and output objects. When ``attach`` specifies a device
  that has a ``swift://`` path, ZeroCloud will run the job with on the
  node holding this object.


The ``help`` Section
--------------------

This section allows you to describe the command line arguments needed
for your application. It is used when you let ``zpm`` auto-generate a
web UI for your application. The keys are:

``description``
  A short description, similar to what programs print when invoked
  with no arguments.

``args``
  A list of arguments. Each list entry is a tuple (really a
  two-element list) with the name of the argument and a corresponding
  help text.


The ``bundling`` Section
------------------------

For ``zpm bundle`` to work, it needs to know which files to include in
the zapp. You specify them here as a list of `glob patterns`__ (such as
``src/*.py``). The patterns are expanded relative to the project root,
i.e., the directory containing the ``zapp.yaml`` file.

.. __: http://en.wikipedia.org/wiki/Glob_%28programming%29


The ``ui`` Section
------------------

You can optionally include a ``ui`` section. If it is left out,
``zpm`` will create a simple web UI for you. The section works like
the ``bundling`` section: you specify a list of glob patterns and
these files will be included in the zapp. The UI files are extracted
when ``zpm deploy`` is run.

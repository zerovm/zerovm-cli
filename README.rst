zpm
===

ZeroVM Package Manager

Supported Python versions: 2.6, 2.7, 3.2, 3.3, and 3.4.

.. image:: http://ci.oslab.cc/job/zpm/badge/icon
   :alt: Build Status
   :target: http://ci.oslab.cc/job/zpm/


Installation
------------

There are currently two options for installing ``zpm``.

- Clone and install::

    $ git clone https://github.com/zerovm/zpm.git
    $ cd zpm
    $ python setup.py install

- Install directly from ``git`` using ``pip``::

    $ pip install git+https://github.com/zerovm/zpm.git


Packaging
---------

Note: This section is interesting only for project maintainers and packagers.
This is not required for installing and using ``zpm``.

1. Install debian packaging dependencies::

    $ sudo apt-get install devscripts debhelper

2. Clone source from Git. Example::

    $ git clone https://github.com/zerovm/zpm.git $HOME/zpm

3. Amend the ``debian/changelog`` manually or using ``dch`` (preferred)

4. Create a gzipped tarball of the zpm source (minus the debian/ dir)::

    $ tar czf ../zpm_0.1.orig.tar.gz * --exclude=debian

   Note that the .tar.gz file name will vary depending on the latest entry
   in the changelog.

5. Build a binary package::

    $ debuild

   or for a source package, ::

    $ debuild -S

zpm
===

Supported Python versions: 2.6, 2.7, 3.3, and 3.4.

.. image:: http://ci.oslab.cc/job/zpm/badge/icon
   :alt: Build Status
   :target: http://ci.oslab.cc/job/zpm/


Documentation
-------------

The documentation is hosted at `docs.zerovm.org`__.

.. __: http://docs.zerovm.org/projects/zerovm-zpm/en/latest/


Installation
------------

You can install ``zpm`` using ``pip``::

   $ pip install zpm


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


Changelog
---------

0.2 (2014-06-30):
   This release drops support for Python 3.2 due to the lack of
   ``u"..."`` literals in that version. Other issues fixed:

   * `#20`_: Set up Debian packaging for zpm.

   * `#31`_: Use ``python-swiftclient`` instead of ``requests`` for
     interacting with Swift.

   * `#37`_: Added a ``zpm execute`` command.

   * `#119`_: ``zpm bundle`` did not raise errors when files in the
     bundling list don't exist.

   * `#122`_: Some ``zpm deploy`` references were not rendering
     correctly in the documentation.

   * `#132`_: Only process UI files ending in ``.tmpl`` as Jinja2
     templates.

0.1 (2014-05-21):
   First release.

.. _#20: https://github.com/zerovm/zpm/issues/20
.. _#31: https://github.com/zerovm/zpm/issues/31
.. _#37: https://github.com/zerovm/zpm/issues/37
.. _#119: https://github.com/zerovm/zpm/issues/119
.. _#122: https://github.com/zerovm/zpm/issues/122
.. _#132: https://github.com/zerovm/zpm/issues/132

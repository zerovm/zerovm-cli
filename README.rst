zpm
===

Supported Python versions: 2.6, 2.7, 3.3, and 3.4.

.. image:: http://ci.oslab.cc/job/zpm/badge/icon
   :alt: Build Status
   :target: http://ci.oslab.cc/job/zpm/


ZPM is a package manger for ZeroVM_. You use it to create and deploy
ZeroVM applications onto ZeroCloud_.

.. _ZeroVM: http://zerovm.org/
.. _ZeroCloud: https://github.com/zerovm/zerocloud/


Documentation
-------------

The documentation is hosted at `docs.zerovm.org`__.

.. __: http://docs.zerovm.org/projects/zerovm-zpm/en/latest/


Installation
------------

You can install ``zpm`` using ``pip``::

   $ pip install zpm


Contact
-------

Please use the `zerovm mailing list`__ on Google Groups for anything
related to zpm. You are also welcome to come by `#zerovm on
irc.freenode.net`__ where the developers can be found.

.. __: https://groups.google.com/forum/#!forum/zerovm
.. __: http://webchat.freenode.net/?channels=zerovm


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


Glossary
========

.. glossary::

   nexe
     A Native Client (NaCl) executable. This is a cross-compiled
     application that can be executed inside the :term:`sandbox`
     created by ZeroVM.

   sandbox
     A secure execution environment created by ZeroVM. A :term:`nexe`
     running inside a sandbox will not be able to access anything
     outside the sandbox.

   system image
     A system image is a pre-installed image that can be referenced in
     a job description. By referencing a system image, you avoid
     uploading a full tarball.

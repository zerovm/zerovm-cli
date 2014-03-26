
The ``zar.json`` File
=====================

The ``zar.json`` plays a central role when writing an application for
deployment on Zwift. This is where you specify things such as:

* Meta-data about the ZAR, such as the name of the author and the
  version number.

* Where to find the NaCl executables ("nexes") and other files that
  make up the ZeroVM applicaiton. These are the files that ``zpm
  bundle`` include into the ZAR.

* Arguments that must be specifed when the application is execution.
  These will be invocation specific.

A sample ``zar.json`` file for a simple "Hello World" application
looks like this:

.. code-block:: json

   {
       "meta" : {
           "name": "hello",
           "Summary": "A small Hello World app",
           "Author-email": "Your Name <your.name@example.net>",
           "Version": "0.1"
       },
       "execution": {
           "groups" : [
               {
                   "name": "hello",
                   "path": "file://python2.7:python",
                   "args": "/hello.py",
                   "devices": [
                       {"name": "python2.7"},
                       {"name": "stdout"}
                   ]
               }
           ]
       },
       "help" : {
           "description": "Enter your name and you will be greeted",
           "args": [
               ["name", "Your name"]
           ]
       },
       "bundling": [
           "hello.py"
       ]
   }

The file is a simple JSON document.

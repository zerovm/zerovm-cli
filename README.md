ZeroVM command line tools
=============

zvsh
----

Supported Python versions: 2.6, 2.7, 3.2, 3.3, and 3.4.

Examples of zvsh usage

----

Run standalone nexe

    $ zvsh path/to/busybox.nexe echo "Hello world"
    Hello world

What did it do?  
Let's save all the intermediate files and look inside

    $ zvsh --zvm-save-dir /tmp/test path/to/busybox.nexe echo "Hello world"
    Hello world
    $ ls -l /tmp/test
    total 84
    drwxrwxr-x  2 pkit  pkit   4096 Dec 10 13:37 .
    drwxrwxrwt 18 root root 69632 Dec 10 13:37 ..
    -rw-rw-r--  1 pkit  pkit    418 Dec 10 13:37 manifest.1
    -rw-rw-r--  1 pkit  pkit    138 Dec 10 13:37 nvram.1
    prw-rw-r--  1 pkit  pkit      0 Dec 10 13:37 stderr.1
    prw-rw-r--  1 pkit  pkit      0 Dec 10 13:37 stdout.1

As we can see there are a minimum 4 files present: two configuration files "manifest.1" and "nvram.1"
and two FIFO pipes that will be attached to stderr and stdout of the running application

    $ cat /tmp/test/manifest.1
    Node = 1
    Version = 20130611
    Timeout = 50
    Memory = 4294967296,0
    Program = /absolute/path/to/busybox.nexe
    Channel = /dev/stdin,/dev/stdin,0,0,4294967296,4294967296,0,0
    Channel = /tmp/test/stdout.1,/dev/stdout,0,0,0,0,4294967296,4294967296
    Channel = /tmp/test/stderr.1,/dev/stderr,0,0,0,0,4294967296,4294967296
    Channel = /tmp/test/nvram.1,/dev/nvram,3,0,4294967296,4294967296,4294967296,4294967296
    
The main manifest configuration file contains all the real machine environment setup.
The interesting parts are:
- path to executable was converted to absolute full path
- the second configuration file /tmp/test/nvram.1 is connected to /dev/nvram device inside the VM
- actual real /dev/stdin on host is connected to /dev/stdin inside VM (will be discussed later)

.

    $ cat /tmp/test/nvram.1
    [args]
    args = busybox echo Hello World
    [mapping]
    channel=/dev/stdin,mode=char
    channel=/dev/stdout,mode=char
    channel=/dev/stderr,mode=char

Secondary configuration file configures the POSIX environment. We have command line arguments in "args" stanza (first argument is argv\[0\]).
And mapping between device name and type of the file in "mapping" stanza

----

Let's run something more complex:

    $ zvsh --zvm-save-dir /tmp/test path/to/busybox.nexe head @path/to/README
    Please see the LICENSE file for details on copying and usage.
    Please refer to the INSTALL file for instructions on how to build.
    
    What is busybox:
    
      BusyBox combines tiny versions of many common UNIX utilities into a single
      small executable.  It provides minimalist replacements for most of the
      utilities you usually find in bzip2, coreutils, dhcp, diffutils, e2fsprogs,
      file, findutils, gawk, grep, inetutils, less, modutils, net-tools, procps,
      sed, shadow, sysklogd, sysvinit, tar, util-linux, and vim.

What did it do?  
We run "head" from inside ZeroVM and apply it to actual file on the host machine "path/to/README"  
Let's see how the manifest and nvram changed

    $ cat /tmp/test/manifest.1 
    Node = 1
    Version = 20130611
    Timeout = 50
    Memory = 4294967296,0
    Program = /absolute/path/to/busybox.nexe
    Channel = /dev/stdin,/dev/stdin,0,0,4294967296,4294967296,0,0
    Channel = /tmp/test/stdout.1,/dev/stdout,0,0,0,0,4294967296,4294967296
    Channel = /tmp/test/stderr.1,/dev/stderr,0,0,0,0,4294967296,4294967296
    Channel = /absolute/path/to/README,/dev/1.README,3,0,4294967296,4294967296,4294967296,4294967296
    Channel = /tmp/test/nvram.1,/dev/nvram,3,0,4294967296,4294967296,4294967296,4294967296
    
Manifest now has entry for the host README file (take note that the path was also converted to absolute)
and it was mapped to "/dev/1.README" device inside the VM

    $ cat /tmp/test/nvram.1 
    [args]
    args = busybox head /dev/1.README
    [mapping]
    channel=/dev/stdin,mode=char
    channel=/dev/stdout,mode=char
    channel=/dev/stderr,mode=char

As we can see in the arguments the path to host file was changed into path to "/dev/1.README" as that's the name of the file inside the VM

----

Now let's use image file

    $ echo "print 'Hello world'" | zvsh --zvm-save-dir /tmp/test --zvm-image path/to/python.tar python
    Hello world

What did it do?  
We run python interpreter inside VM and submit it a script "print 'Hello world'" through the host /dev/stdin  
Let's see the configuration

    $ cat /tmp/test/manifest.1 
    Node = 1
    Version = 20130611
    Timeout = 50
    Memory = 4294967296,0
    Program = /tmp/test/boot.1
    Channel = /dev/stdin,/dev/stdin,0,0,4294967296,4294967296,0,0
    Channel = /tmp/test/stdout.1,/dev/stdout,0,0,0,0,4294967296,4294967296
    Channel = /tmp/test/stderr.1,/dev/stderr,0,0,0,0,4294967296,4294967296
    Channel = /absolute/path/to/python.tar,/dev/1.python.tar,3,0,4294967296,4294967296,4294967296,4294967296
    Channel = /tmp/test/nvram.1,/dev/nvram,3,0,4294967296,4294967296,4294967296,4294967296

As we can see the path to python.tar was added to manifest and the device is named "/dev/1.python.tar"
We also see that the "Program" now points to "/tmp/test/boot.1" as this is a path to python executable that was temporarily extracted from the python.tar

    $ tar tvf path/to/python.tar
    drwxr-xr-x pkit/pkit           0 2013-12-03 20:15 include/
    drwxr-xr-x pkit/pkit           0 2013-12-03 20:15 include/python2.7/
    -rw-r--r-- pkit/pkit       21113 2013-12-03 20:15 include/python2.7/Python-ast.h
    -rw-r--r-- pkit/pkit        4329 2013-12-03 20:15 include/python2.7/Python.h
    -rw-r--r-- pkit/pkit       45015 2013-12-03 20:15 include/python2.7/abstract.h
    -rw-r--r-- pkit/pkit        1099 2013-12-03 20:15 include/python2.7/asdl.h
    -rw-r--r-- pkit/pkit         230 2013-12-03 20:15 include/python2.7/ast.h
    -rw-r--r-- pkit/pkit         792 2013-12-03 20:15 include/python2.7/bitset.h
    -rw-r--r-- pkit/pkit         912 2013-12-03 20:15 include/python2.7/boolobject.h
    ........
    ........
    drwxr-xr-x pkit/pkit           0 2013-12-03 20:15 share/man/man1/
    -rw-r--r-- pkit/pkit       14576 2013-12-03 20:15 share/man/man1/python2.7.1
    -rwxrwxr-x pkit/pkit    21011528 2013-12-03 20:15 python

Python executable is at the end of python.tar archive and is just called "python" this is what we supplied in the command line, 
and this is what will get extracted as "/tmp/test/boot.1"

    $ cat /tmp/test/nvram.1 
    [args]
    args = python
    [fstab]
    channel=/dev/1.python.tar,mountpoint=/,access=ro,removable=no
    [mapping]
    channel=/dev/stdout,mode=char
    channel=/dev/stderr,mode=char

Here a new stanza "fstab" is added. It maps the image to the mount point "/", which means that files inside the tar will be mounted as a root file system.  
Access to files is "read-only" and the tar is "not removable" (discussion about removable devices is out of the scope of this document).  
The /dev/stdin is also not a "char" device anymore, because we connected it to a pipe at the moment (remember "echo .... | zvsh ...." ?).  

How to create a tar image?  
It's simple, really, just add all the files you want there and supply it to the zvsh as `--zvm-image` argument.  
Any tar archive will be loaded and injected as a file system. You can supply several `--zvm-image` arguments to zvsh 
all images will be loaded and mounted.
If you want your image to be "read-write" or you want to mount it to a different path than "/" 
just add it to the argument like this: `--zvm-image path/to/image.tar,/mount/point,rw`

zvapp
----

A tool to run servlets or cluster images on one machine, without using Openstack Swift infrastructure.

Please consider reading the [servlet-related documents] (https://github.com/zerovm/zerocloud/tree/master/doc) before proceeding.


Using zvapp we can run several types of configurations.

Run servlet description file (JSON)

----

    $ zvapp --swift-account-path /home/user/swift job.json

Here we run a JSON job description that references swift:// urls.  
Each url should be mapped to a local file/directory. Here we use `--swift-account-path` for that.
It points to a local dir where all the files are placed in same hierarchy as in Swift account.  
Example:

    /home/user/swift
    \ container1
       \ object1
       \ object2
    \ container2
       \ object3
       \ object4

    swift://account/container1/object2 -> /home/user/swift/container1/object2

Note: any account name will point to the same /home/user/swift directory

If we want to use directory per account, we can use `--swift-root-path` directive.  
Example:

    --swift-root-path /home/user/swift

    /home/user/swift
    \ account1
       \ container1
          \ object1
          \ object2
       \ container2
          \ object3
          \ object4

    swift://account1/container1/object2 -> /home/user/swift/account1/container1/object2


Run from application root

----

    $ zvapp --swift-account-path /home/user/swift path/to/app/root

Application root should have `boot/system.map` or `boot/cluster.map` file. The application job will be loaded from there.  
You can also reference any `swift://` URLs inside the job, as in any other job description file.

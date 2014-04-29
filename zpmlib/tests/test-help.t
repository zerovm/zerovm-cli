
No arguments:

  $ zpm help
  usage: zpm [-h] COMMAND ...
  
  ZeroVM Package Manager
  
  optional arguments:
    -h, --help  show this help message and exit
  
  subcommands:
    available subcommands
  
    COMMAND
      bundle    Bundle a ZeroVM application This command creates a Zapp using
                the instructions in ``zapp.yaml``. The file is read from the
                project root.
      deploy    Deploy a ZeroVM application This deploys a zapp onto Swift. The
                zapp can be one you have downloaded or produced yourself :ref
                :`zpm-bundle`. You will need to know the Swift authentication
                URL, username, password, and tenant name. These can be supplied
                with command line flags (see below) or you can set the
                corresponding environment variables. The environment variables
                are the same as the ones used by the `Swift command line tool
                <http://docs.openstack.org/ user-
                guide/content/swift_commands.html>`_, so if you're already using
                that to upload files to Swift, you will be ready to go.
      help      Show this help
      new       Create a default ZeroVM application ``zapp.yaml`` specification
                in the target directory. If no directory is specified,
                ``zapp.yaml`` will be created in the current directory.
  
  See 'zpm <command> --help' for more information on a specific command.

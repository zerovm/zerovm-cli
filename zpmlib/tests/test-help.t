
Main help text is shown when no command is given:

  $ zpm help
  usage: zpm [-h] COMMAND ...
  
  ZeroVM Package Manager
  
  optional arguments:
    -h, --help  show this help message and exit
  
  subcommands:
    available subcommands
  
    COMMAND
      bundle    Bundle a ZeroVM application
      deploy    Deploy a ZeroVM application
      help      Show this help
      new       Create template ``zapp.yaml`` file
      version   Show the version number
  
  See 'zpm <command> --help' for more information on a specific command.

Test with existing command:

  $ zpm help new
  usage: zpm new [-h] [WORKING_DIR]
  
  Create a default ZeroVM application ``zapp.yaml`` specification in the target
  directory. If no directory is specified, ``zapp.yaml`` will be created in the
  current directory.
  
  positional arguments:
    WORKING_DIR  Non-existent or empty directory (default: .)
  
  optional arguments:
    -h, --help   show this help message and exit

Test with non-existing command:

  $ zpm help no-such-command
  no such command: no-such-command
  usage: zpm [-h] COMMAND ...
  
  ZeroVM Package Manager
  
  optional arguments:
    -h, --help  show this help message and exit
  
  subcommands:
    available subcommands
  
    COMMAND
      bundle    Bundle a ZeroVM application
      deploy    Deploy a ZeroVM application
      help      Show this help
      new       Create template ``zapp.yaml`` file
      version   Show the version number
  
  See 'zpm <command> --help' for more information on a specific command.

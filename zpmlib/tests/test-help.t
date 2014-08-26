
Main help text is shown when no command is given:

  $ zpm help
  usage: zpm [-h] [--version] COMMAND ...
  
  ZeroVM Package Manager
  
  optional arguments:
    -h, --help  show this help message and exit
    --version   show the version number and exit
  
  subcommands:
    available subcommands
  
    COMMAND
      auth      Get auth token and storage URL information
      bundle    Bundle a ZeroVM application
      deploy    Deploy a ZeroVM application
      execute   Remotely execute a ZeroVM application.
      help      Show this help
      new       Create template zapp.yaml file
      version   Show the version number
  
  See 'zpm <command> --help' for more information on a specific command.

Test with existing command:

  $ zpm help new
  usage: zpm new [-h] [--log-level {debug,info,warning,error,critical}]
                 [WORKING_DIR]
  
  Create a default ZeroVM application zapp.yaml specification in the target
  directory. If no directory is specified, zapp.yaml will be created in the
  current directory.
  
  positional arguments:
    WORKING_DIR           Non-existent or empty directory (default: .)
  
  optional arguments:
    -h, --help            show this help message and exit
    --log-level {debug,info,warning,error,critical}, -l {debug,info,warning,error,critical}
                          Defaults to 'warn' (default: warning)


Test with non-existing command:

  $ zpm help no-such-command
  no such command: no-such-command
  usage: zpm [-h] [--version] COMMAND ...
  
  ZeroVM Package Manager
  
  optional arguments:
    -h, --help  show this help message and exit
    --version   show the version number and exit
  
  subcommands:
    available subcommands
  
    COMMAND
      auth      Get auth token and storage URL information
      bundle    Bundle a ZeroVM application
      deploy    Deploy a ZeroVM application
      execute   Remotely execute a ZeroVM application.
      help      Show this help
      new       Create template zapp.yaml file
      version   Show the version number
  
  See 'zpm <command> --help' for more information on a specific command.

Test default value shown when flag takes default from environment:

  $ zpm help deploy
  usage: zpm deploy [-h] [--execute] [--summary] [--force]
                    [--auth-version {1.0,2.0}] [--auth AUTH] [--user USER]
                    [--key KEY] [--os-auth-url OS_AUTH_URL]
                    [--os-tenant-name OS_TENANT_NAME]
                    [--os-username OS_USERNAME] [--os-password OS_PASSWORD]
                    [--no-ui-auth]
                    [--log-level {debug,info,warning,error,critical}]
                    target zapp
  
  This deploys a zapp onto Swift. The zapp can be one you have downloaded or
  produced yourself with "zpm bundle". You will need to know the Swift
  authentication URL, username, password, and tenant name. These can be supplied
  with command line flags (see below) or you can set the corresponding
  environment variables. The environment variables are the same as the ones used
  by the Swift command line tool, so if you're already using that to upload
  files to Swift, you will be ready to go.
  
  positional arguments:
    target                Deployment target (Swift container name)
    zapp                  A ZeroVM application
  
  optional arguments:
    -h, --help            show this help message and exit
    --execute             Immediately execute the deployed Zapp (for testing)
    --summary, -s         Show execution summary table (use with `--execute`)
    --force, -f           Force deployment to a non-empty container
    --auth-version {1.0,2.0}, -V {1.0,2.0}
                          Swift auth version (default: 1.0)
    --auth AUTH, -A AUTH  (Auth v1.0) URL for obtaining an auth token (default:
                          $ST_AUTH)
    --user USER, -U USER  (Auth v1.0) User name for obtaining an auth token
                          (default: $ST_USER)
    --key KEY, -K KEY     (Auth v1.0) Key for obtaining an auth token (default:
                          $ST_KEY)
    --os-auth-url OS_AUTH_URL
                          (Auth v2.0) OpenStack auth URL (default: $OS_AUTH_URL)
    --os-tenant-name OS_TENANT_NAME
                          (Auth v2.0) OpenStack tenant (default:
                          $OS_TENANT_NAME)
    --os-username OS_USERNAME
                          (Auth v2.0) OpenStack username (default: $OS_USERNAME)
    --os-password OS_PASSWORD
                          (Auth v2.0) OpenStack password (default: $OS_PASSWORD)
    --no-ui-auth          Do not generate any authentication code for the web UI
    --log-level {debug,info,warning,error,critical}, -l {debug,info,warning,error,critical}
                          Defaults to 'warn' (default: warning)

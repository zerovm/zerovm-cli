
Test bad --auth-version:

  $ zpm deploy --auth-version 1.5
  usage: zpm deploy [-h] [--execute] [--summary] [--force]
                    [--auth-version {1.0,2.0}] [--auth AUTH] [--user USER]
                    [--key KEY] [--os-auth-url OS_AUTH_URL]
                    [--os-tenant-name OS_TENANT_NAME]
                    [--os-username OS_USERNAME] [--os-password OS_PASSWORD]
                    [--no-ui-auth]
                    [--log-level {debug,info,warning,error,critical}]
                    target zapp
  zpm deploy: error: argument --auth-version/-V: invalid choice: '1.5' (choose from '1.0', '2.0')
  [2]

Test deploy with no credentials set:

  $ zpm deploy target zapp
  
  Error:
  Auth version 1.0 requires ST_AUTH, ST_USER, and ST_KEY environment variables
  to be set or overridden with -A, -U, or -K.
  
  Auth version 2.0 requires OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, and
  OS_TENANT_NAME OS_TENANT_ID to be set or overridden with --os-auth-url,
  --os-username, --os-password, --os-tenant-name or os-tenant-id. Note:
  adding "-V 2" is necessary for this.
  [1]

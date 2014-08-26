
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

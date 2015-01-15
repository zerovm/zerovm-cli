
Test creating new project dir:

  $ zpm new foo
  Created 'foo/zapp.yaml'
  Created 'foo/.zapp'
  Created 'foo/.zapp/tox.ini'
  $ grep '^  name:' foo/zapp.yaml
    name: "foo"

Test inside existing directory:

  $ mkdir bar
  $ cd bar
  $ zpm new
  Created './zapp.yaml' (glob)
  Created './.zapp'
  Created './.zapp/tox.ini'
  $ cd ..

Test with exising zapp.yaml:

  $ zpm new bar
  'bar/zapp.yaml' already exists!

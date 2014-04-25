
Test creating new project dir:

  $ zpm new foo
  Created 'foo/zapp.yaml'
  $ grep '^  name:' foo/zapp.yaml
    name: "foo"

Test inside existing directory:

  $ mkdir bar
  $ cd bar
  $ zpm new
  Created '*/bar/zapp.yaml' (glob)
  $ cd ..

Test with exising zapp.yaml:

  $ zpm new bar
  'bar/zapp.yaml' already exists!

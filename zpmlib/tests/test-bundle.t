
Test bundling with auto-generated UI:

  $ mkdir foo
  $ cd foo
  $ touch a.txt
  $ cat > zapp.yaml <<EOF
  > execution:
  >   groups:
  >     - path: file://python2.7:python
  >       args: foo.py
  >       name: foo
  >       devices:
  >       - name: python2.7
  > meta:
  >   name: "foo"
  > help:
  >   args: [ ]
  > bundling:
  >   - "*.py"
  >   - a.txt
  > EOF

  $ zpm bundle --log-level info
  INFO:adding foo.json
  INFO:adding zapp.yaml
  WARNING:pattern '*.py' in section 'bundling' matched no files
  INFO:adding /*/foo/a.txt (glob)
  INFO:adding index.html
  INFO:adding style.css
  INFO:adding zerocloud.js
  created foo.zapp

  $ tar -tf foo.zapp
  foo.json
  zapp.yaml
  a.txt
  index.html
  style.css
  zerocloud.js

Test bundling with UI

  $ touch foo.html myzerocloud.js
  $ cat >> zapp.yaml <<EOF
  > ui:
  >   - foo.html
  >   - myzerocloud.js
  > EOF

  $ zpm bundle --log-level info
  INFO:adding foo.json
  INFO:adding zapp.yaml
  WARNING:pattern '*.py' in section 'bundling' matched no files
  INFO:adding /*/foo/a.txt (glob)
  INFO:adding /*/foo/foo.html (glob)
  INFO:adding /*/foo/myzerocloud.js (glob)
  created foo.zapp
  $ tar -tf foo.zapp
  foo.json
  zapp.yaml
  a.txt
  foo.html
  myzerocloud.js


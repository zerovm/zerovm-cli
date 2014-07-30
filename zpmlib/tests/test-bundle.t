
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
  INFO:zpmlib.zpm: adding boot/system.map
  INFO:zpmlib.zpm: adding zapp.yaml
  WARNING:zpmlib.zpm: pattern '*.py' in section 'bundling' matched no files
  INFO:zpmlib.zpm: adding /*/foo/a.txt (glob)
  INFO:zpmlib.zpm: adding index.html.tmpl
  INFO:zpmlib.zpm: adding style.css
  INFO:zpmlib.zpm: adding zerocloud.js
  created foo.zapp

  $ tar -tf foo.zapp
  boot/system.map
  zapp.yaml
  a.txt
  index.html.tmpl
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
  INFO:zpmlib.zpm: adding boot/system.map
  INFO:zpmlib.zpm: adding zapp.yaml
  WARNING:zpmlib.zpm: pattern '*.py' in section 'bundling' matched no files
  INFO:zpmlib.zpm: adding /*/foo/a.txt (glob)
  INFO:zpmlib.zpm: adding /*/foo/foo.html (glob)
  INFO:zpmlib.zpm: adding /*/foo/myzerocloud.js (glob)
  created foo.zapp
  $ tar -tf foo.zapp
  boot/system.map
  zapp.yaml
  a.txt
  foo.html
  myzerocloud.js


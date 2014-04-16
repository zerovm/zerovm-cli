
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

  $ zpm bundle
  adding foo.json
  adding /*/foo/a.txt (glob)
  adding /*/foo/zapp.yaml (glob)
  adding index.html
  adding style.css
  adding zebra.js
  created foo.zapp

  $ tar -tf foo.zapp
  foo.json
  a.txt
  zapp.yaml
  index.html
  style.css
  zebra.js

Test bundling with UI

  $ touch foo.html myzebra.js
  $ cat >> zapp.yaml <<EOF
  > ui:
  >   - foo.html
  >   - myzebra.js
  > EOF

  $ zpm bundle
  adding foo.json
  adding /*/foo/a.txt (glob)
  adding /*/foo/zapp.yaml (glob)
  adding /*/foo/foo.html (glob)
  adding /*/foo/myzebra.js (glob)
  created foo.zapp
  $ tar -tf foo.zapp
  foo.json
  a.txt
  zapp.yaml
  foo.html
  myzebra.js


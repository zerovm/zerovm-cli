#!/bin/bash

WORKSPACE=$HOME/workspace
DEPS="python-debian debhelper devscripts python-pip python-setuptools"
DEPS="$DEPS git mercurial"

sudo apt-get update
sudo apt-get install --yes $DEPS

# Install multiple versions of python to test compatibility
sudo add-apt-repository ppa:fkrull/deadsnakes --yes
sudo apt-get update
sudo apt-get install --yes python2.6 python3.3 python3.4

sudo pip install tox

wget https://raw.githubusercontent.com/zerovm/zvm-jenkins/master/packager.py -O /tmp/packager.py

rsync -az --exclude=contrib/jenkins/.* /jenkins/ $WORKSPACE
cd $WORKSPACE
# Allow PRs to be checked out
git fetch origin +refs/pull/*:refs/remotes/origin/pr/*

# Jenkins can now run test commands

#!/bin/bash
set -e

SOURCE=/mnt/sshd/hab/hikey
REFERENCE=/mnt/sshd/devel/optee_projects/reference

mkdir -p $SOURCE
cd $SOURCE
source ~/bin/init_python2
#repo init -u https://github.com/OP-TEE/manifest.git -m hikey.xml --reference $REFERENCE
repo forall -c 'echo Cleaning ... $REPO_PATH && git clean -xdf && git checkout -f'
#repo sync -j3 -d

ln -sf $REFERENCE/toolchains $SOURCE/
cd build

# TODO: Remove this, just for testing
ln -sf hikey.mk Makefile

make -j8 2>&1 | tee build.log

echo "Done building HiKey"

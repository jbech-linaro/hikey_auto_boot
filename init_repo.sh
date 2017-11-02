#!/bin/bash
set -e
export PS1="foo $$ "

# Needs to be synced between this script and build.sh
SOURCE=/home/optee/devel/hikey
REFERENCE=/home/optee/devel/reference

# An extra check to avoid wiping the entire hard drive.
if [ "$SOURCE" == "" ] || [ "$SOURCE" == "/" ]; then 
	echo "SOURCE not set or dangerous value in use!"
	exit 1
fi

rm -rf $SOURCE
mkdir -p $SOURCE
cd $SOURCE

repo init -u https://github.com/OP-TEE/manifest.git -m hikey.xml --reference $REFERENCE
repo forall -c 'echo Cleaning ... $REPO_PATH && git clean -xdf && git checkout -f'
repo sync -j3 -d

ln -sf $REFERENCE/toolchains $SOURCE/

echo "Done setting up HiKey project"

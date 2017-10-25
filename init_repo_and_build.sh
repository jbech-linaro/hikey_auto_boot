#!/bin/bash
set -e

# WARNING!!! Do not set SOURCE to an empty string or just "/" since that will
# wipe your hard drive!!!
SOURCE=/mnt/sshd/hab/hikey
REFERENCE=/mnt/sshd/devel/optee_projects/reference

URL=""
REVISION=""
NAME=""

if [ "$1" ]; then
	URL=$1
fi

if [ "$2" ]; then
	REVISION=$2
fi

if [ "$3" ]; then
	NAME=$3
fi

echo "url: $URL"
echo "revision: $REVISION"
echo "name: $NAME"

#rm -rf $SOURCE
mkdir -p $SOURCE
cd $SOURCE
source ~/bin/init_python2
repo init -u https://github.com/OP-TEE/manifest.git -m hikey.xml --reference $REFERENCE
repo forall -c 'echo Cleaning ... $REPO_PATH && git clean -xdf && git checkout -f'
rm -rf $SOURCE/out
#repo sync -j3 -d

ln -sf $REFERENCE/toolchains $SOURCE/

# We have all three arguements
if [ "$#" -eq  "3" ]; then
	cd $NAME
	git clean -xdf
	nbr_remotes=$(git remote -v | wc -l)
	echo $nbr_remotes

	# TODO: Hack to avoid getting error message if remote already exists
	if [ "$nbr_remotes" -eq "4" ] 2>/dev/null; then
		git remote remove pr_creator
	fi

	git remote add pr_creator $URL
	git fetch pr_creator
	git checkout $REVISION
fi

cd ../build


# TODO: Remove this, just for testing
ln -sf hikey.mk Makefile

make -j8 2>&1 | tee build.log

echo "Done building HiKey"

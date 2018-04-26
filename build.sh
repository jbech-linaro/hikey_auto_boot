#!/bin/bash
export PS1="$$ "

cd /home/optee/devel/hikey/build

# This magic here is getting the return value from make and not tee ...
(make -j8 CFG_DRAM_SIZE_GB=1 CFG_FLASH_SIZE=4 2>&1 | tee build.log; test ${PIPESTATUS[0]} -eq 0)

if [[ "$?" -eq "0" ]]; then
	echo "Done building HiKey"
else
	echo "Failed building HiKey"
fi

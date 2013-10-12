#!/bin/sh

# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

# v1.0 - 2013.9.22
# project inited.

if [ -d 'fakeroot' ]; then
	rm -rvf fakeroot
fi

PYLIB='fakeroot/usr/lib/python3/dist-packages/'
APP='kwplayer'

mkdir -vp fakeroot/usr/bin fakeroot/DEBIAN $PYLIB

cp -v ../kwplayer fakeroot/usr/bin/
cp -rvf ../kuwo $PYLIB/
rm -rvf $PYLIB/kuwo/__pycache__
cp -rvf ../mutagenx $PYLIB/
rm -rvf $PYLIB/mutagenx/__pycache__
cp -rvf ../share fakeroot/usr/share
cp -vf control fakeroot/DEBIAN/

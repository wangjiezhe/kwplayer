#!/bin/sh

# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

# Step 1 of i18n - generate po file

PO_DIR='../po'
GLADE='../share/kuwo/ui/menus.ui'

intltool-extract --type="gettext/glade" $GLADE
mv ${GLADE}.h .

xgettext --language=Python --keyword=_ --keyword=N_ --output kuwo.pot ../kuwo/*.py menus.ui.h

rm -vf menus.ui.h
mv kuwo.pot $PO_DIR
echo 'kuwo.pot genrated..'

#cd $PO_DIR
# generate zh_CN, zh_TW po files
#msginit --input=kuwo.pot --locale=zh_CN
#echo 'zh_CN.po generated..'
#msginit --input=kuwo.pot --locale=zh_TW
#echo 'zh_TW.po generated..'

exit 0

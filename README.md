关于
====
kwplayer是linux桌面下的网络音乐播放工具, 它使用kuwo.cn的音乐资源.

经过测试, kwplayer可以在以下系统中运行:

* Debian sid
* Debian testing
* Debian whezy
* Ubuntu 13.10 Beta
* Ubuntu 13.04
* Ubuntu 12.10
* Ubuntu 12.04
* Gentoo
* Fedora 20 (Alpha)
* Fedora 19
* Arch Linux


自动安装
=======
推荐自动安装, 除非你愿意手动维护下面那么多的软件包依赖关系.

Debian系列, 直接安装kwplayer.deb包就行了, 它会处理好安装问题.

关于为其它包管理系统打包的问题, 我一个人没能力完全维护, 比如rpm, gentoo的
ebuild, arch的pkgbuild. 如果有哪位朋友对其中比较熟悉的, 并且乐意提供帮助的,
请联系我:
<a href="mailto:gsushzhsosgsu@gmail.com" title="LiuLang">LiuLang</a>

以后尽可能提供rpm等安装包.

所有打好的包都转移到了
[kwplayer-packages](https://github.com/LiuLang/kwplayer-packages "kwplayer-packages")
这个项目中, 请转到那里去下载.

手动安装
========
手动安装分两部分, 一是安装kwplayer的依赖包, 二是安装kwplayer. 有太多linux
发行版, 这里只以四个主要的发行版为例来说明.


Debian 中手动安装依赖包
---------------------
手动安装的话, 需要手动安装一些依赖包, 以Debian sid中安装为例, 它们是:

* python3 - 推荐python3.3以上的版本, 不然mutagenx模块无法使用(用于消除mp3/ape乱码的).
* python3-dbus
* python3-gi  -  gkt3的python3绑定(Fedora中叫做python3-gobject);
* gstreamer1.0-plugins-base
* gstreamer1.0-plugins-good
* gstreamer1.0-plugins-ugly
* gstreamer1.0-libav 音频/视频的解码器
* gstreamer1.0-x
* gir1.2-gstreamer-1.0,
* gir1.2-gst-plugins-base-1.0
* gir1.2-notify-0.7 - notify 的Gtk绑定.
* gstreamer1.0-pulseaudio
* leveldb - 强大的NoSQL数据库(用于缓存数据);
* python3-leveldb  -  leveldb的python3绑定(Fedora中是python3-plyvel);
Ubuntu 12.04中缺少了这个包, 请使用`# pip3 install plyvel` 来安装, 安装时需要
优先安装python3-dev, libleveldb-dev这两个头文件.
* python3-mutagenx - 这个需要手动安装. 可以在这里下载:
<https://github.com/LordSputnik/mutagen>, 如果你没有python3.3 比如Debian
Wheezy, Ubuntu 12.04, 就不需要安装这个模块了, 因为它不支持python3.2以下的
版本. `# pip3 install mutagenx`
* python3-xlib - X的底层接口, 这个是从python-xlib迁移过来的, 刚刚完成.
可以在这里找到<https://github.com/LiuLang/python3-xlib>,
`# pip3 install python3-xlib`
* python3-keybinder 这个是用于绑定全局快捷键.
<https://github.com/LiuLang/python3-keybinder>
`# pip3 install python3-keybinder`

上面是gstreamer1.0的, 对于旧的gstreamer0.10版, 需要大致修改一下.

[注]: pip3是python3-pip包提供的命令, 它是python3的一个包管理器, 可以自动安装
更新, 卸载python3的模块包, 相录于debian中的dpkg. 有些系统(比如Arch Linux),
已经将python3作为了默认的python环境, 所以只需要用pip命令就可以了.

Fedora 中手动安装依赖包
-----------------------
对于Fedora, 我专门安装并测试了Fedora 19 amd64, 也很简单, 需要这些操作:

* 更新系统. 我用的是mirrors.163.com这个更新源, 速度很好.
* 使用rpmfushion, 可以参考这篇文章:<http://blog.csdn.net/sabalol/article/details/9286073>
* python3-dbus
* gstreamer1-plugins-good
* gstreamer1-plugins-ugly
* gstreamer1-libav
* 安装leveldb 和 python3-plyvel
* 安装python3-mutagenx.
* 安装python3-xlib 和 python3-keybinder

在Arch 中手动安装依赖包
-----------------------
@mindcat为arch写的pkgbuild, 使用了github上的最新的代码:
<https://aur.archlinux.org/packages/kwplayer-git/?setlang=en>
而@shmilee 写的另一个pkgbuild, 是基于kwplayer的发行版本, 可以在这里得到:
<0https://aur.archlinux.org/packages/kwplayer/>

[注:] arch中, 默认的python版本是python3.

* python-dbus
* gst-plugins-base 根据@mindcat的测试补充进来的
* gst-plugins-good | gstreamer.01.0-good-plugins
* gst-plugins-ugly | gstremaer0.10-ugly-plugins
* gst-libav
* gstreamer | gstreamer0.10
* python-gobject
* leveldb
* py-leveldb | plyvel 这两个任选一个, 它们分别由不同的团队在维护:
<http://code.google.com/p/py-leveldb/> 和
<https://github.com/wbolster/plyvel>
比如, 可以: `# pip install plyvel`
* gnome-icon-theme-symbolic-git
* python3-mutagenx - ` # pip install mutagenx`
* python3-xlib - `# pip install python3-xlib`
* python3-keybinder - `# pip install python3-keybinder`


Gentoo 中手动安装依赖包
-----------------------
没条件测试, 如果有哪位gentoo的朋友写了ebuild, 请一定分享出来, 以方便其他朋友使用;

安装kwplayer
------------
根据你的发行版, 按照上面的方法安装好依赖包之后, 就可以开始安装kwplayer本身了.

* 安装: `# pip3 install kwplayer`
* 更新: `# pip3 install --upgrade kwplayer`


Tips & Tricks
=============
* 在gnome-shell中, 可以安装mediaplayer这个扩展, 与kwplayer结合使用, 很方便.
可以在这里进行安装:
<https://extensions.gnome.org/extension/55/media-player-indicator/>
* 需要批量下载歌曲的话, 可以把它们加入到"正在缓存"(caching)这个播放列表里,
在这个播放列表的上方有一个"开始缓存"的按纽, 你明白的~
* 播放歌曲时把鼠标放到左上角的歌手头像上, 可以显示歌手的基本信息.
* 播放歌曲时双击左上角的歌手的头像可以在播放列表中定位正在播放的这首歌.
* 播放列表中的歌曲可以直接拖放到其它列表, 支持键盘操作, 比如Ctrl+A全选;
选择歌曲时按下Ctrl键可多选. 按Del键可以删除选中的歌曲.
* 从播放列表中删除歌曲时, 按下Shift键, 可以同时删除磁盘上的mp3等文件.
* 对于小屏的笔记本来说, 全屏播放MV的效果更好.
* 尽量不下载ape格式的歌曲, 因为这种格式的文件实在太大了.
* 歌词的背景图片的分辨率是1024x768的, 如果你的显示屏比较大的话, 背景图会平
铺显示, 并且会重复, 这是因为GtkCssProvider还不支持设定background-image的重
复方式, 估计在以后的版本中, 它会加入吧.


Q&A
===
问: 为什么只使用mp3(192K)和ape两种格式的音乐?

答: 其它格式都不太适用, 比如wma的音质不好; 而192K的mp3对于一般用户已经足够好了; 而对于音乐发烧友来说, 320K的mp3格式的质量仍然是很差劲的, 只有ape才能满足他(她)们的要求. 举例来说, 192K的mp3大小是4.7M, 320K的mp3是7.2M, 而对应的ape格式的是31.5M左右, 这就是差距.
总之, 这两种格式足够了.

问: 为什么不能用它来打开/管理本地的音乐?

答: 没有必要. 因为Linux桌面已经有不少强大的音乐管理软件了, 像rhythmbox, audacity, amarok等, 干嘛要加入一些重复的功能?

问: kwplayer 中怎样代理上网?
答: 它使用系统默认的http代理. 比如在gnome桌面里,
打开"系统设置"面板 -> "网络" -> "代理", 选择"手动", 然后为http设置代理.
也可以在在终端中使用代理, 比如:
`$ export http_proxy="http://127.0.0.1:8080"; kwplayer`
就可以了.

问: 启动时出现这个错误(arch linux中), `Xlib.error.DisplayConnectionError: Can't connect to display ":0.0": b'No protocol specified\n'`
答: 因为Arch中启用了Host-based access, 默认情况下, 多媒体键是不可用的. 现在的
办法是关闭host-based acces, `$ xhost +`. 这个方法是@shmile提供的. 更多信息, 可以
参考<https://wiki.archlinux.org/index.php/Xhost>以及
<http://en.wikipedia.org/wiki/X_Window_authorization>

也可以将`xhost + >/dev/null` 这条命令加入到系统启动脚本中, 这样的话, 系统启动时
就会自动关闭Host-based access了.


KNOWN BUGS
============
* 对于Debian Wheezy, 由于gstreamer0.1中不能直接把视频渲染到DrawingArea上,
在播放MV时视频窗口被被弹出, 这个bug我暂时不能修复; 这个bug在2011年就有人发
现, 可一直没有得到修复, 再加上后来推出了gstreamer1.0, 看来就更难了.
* 在退出时, plyvel会报错. 使用python3-leveldb模块, 就不会这样, 主要是
新版(plyvel-0.6)存在一些问题, 估计等到0.7版, 就能被修复了.


TODO
====
* <del>播放列表支持歌曲的拖放</del> (已完成).
* <del>在gnome3.10中, 屏幕锁定时, 仍然能控制播放器, 比如下一曲, 暂停等</del>
(已完成).
* <del>加入dbus</del> (已完成).
* <del>支持键盘上的多媒体键</del> (已完成).
* <del>支持Debian stable</del> (已支持)
* <del>为Ubuntu创建PPA</del> (已放弃, 因为它不能保证与debian等发行版的兼容性)
* <del>优化歌词的显示效果</del> (已重写, 使用了Gtk3 CSS)
* <del>将播放列表中的音乐导出到其它目录, 也可以导出到手机中</del> (已完成)
* <del>自动修复mp3的tag编码</del> (已完成)
* <del>支持打开/管理本地的多媒体资源</del>
* <del>使用gettext国际化(i18n)</del> (已完成)
* <del>加入简体中文(zh_CN.po)</del> (已完成)
* <del>加入繁体中文(zh_TW.po)</del> (已完成)
* <del>全屏播放</del> (已完成)
* <del>实时的简体与繁体的转换, 对于使用繁体中文显示的朋友来说会非常方便,
因为显面中的简体中文会自动转为繁体来显示, 并且也可以使用繁体来搜索</del>
(已放弃)
* 优化Gstreamer, 修复播放MV时的无声bug.


截图
====
在gdm的锁屏界面也可以控制kwplayer:
<img src="screenshot/kwplayer-on-gdm-screen.jpg?raw=true" title="kwplayer on gdm screen" />

播放列表:
<img src="screenshot/playlist.png?raw=true" title="播放列表" />

电台:
<img src="screenshot/radio.png?raw=true" title="电台" />

MV:
<img src="screenshot/MV.png?raw=true" title="MV" />

搜索:
<img src="screenshot/search.png?raw=true" title="搜索" />

选择音乐格式:
<img src="screenshot/format.png?raw=true" title="选择音乐格式" />

其它的:
<img src="screenshot/others.png?raw=true" title="其他的" />


COPYRIGHT
========
软件本身使用GNU General Public License v3协议发布, 协议内容请参看LICENSE文件.

本人不存储任何侵权的多媒体资源供网友下载, 软件中获取的网络资源, 包括但不限
于图片, 音频文件, 视频文件, 都来自于kuwo.cn这个网站, 因使用本程序引起的一
切侵权问题由使用者本人承担.

软件名称kwplayer没有中文名, 不与"酷我音乐盒"等对应.

有任何问题, 请联系我: LiuLang <gsushzhsosgsu@gmail.com>

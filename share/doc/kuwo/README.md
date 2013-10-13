关于
====
kwplayer是linux桌面下的网络音乐播放工具, 它使用了kuwo.cn的音乐资源.
注意: 程序尚在开发当中, 可能会出现各种问题, 欢迎提交bug.

安装
====
debian系列的, 需要手动安装一些依赖包, 它们是:

* python3 - 推荐python3.3以上的版本, 不然mutagen模块无法使用(用于消除mp3/ape乱码的).
* python3-gi  -  gkt3的python3绑定(Fedora中叫做python3-gobject);
* python3-cairo -  cairo的python3绑定(用于实现显示特效);
* python3-gi-cairo - 在GObject中用到的cairo的python3绑定;
* gstreamer1.0-x - gtk的多媒体框架;
* gstreamer1.0-libav  -  gstreamer的编码/解码库;
* gstreamer1.0-plugins-base - gstreamer的基本核心包
* gir1.2-gstreamer-1.0, gir1.2-gst-plugins-base-1.0 - 这两个是gst的gobject
绑定, 这样就可以解决ImportError: cannot import name GstVideo 之类的错误.
* leveldb - 强大的NoSQL数据库(用于缓存数据);
* python3-leveldb  -  leveldb的python3绑定(Fedora中是python3-plyvel);
* 安装好gstreamer后, 可能需要重启一下系统, 至少在我这里测试时需要这样.

也可以直接运行build/下面的脚本, 生成deb包, 它会自动处理依赖关系, 不需要手动
安装上面列出的那些软件包, 需要以下的操作:

* 更新系统
* 下载本页面右侧的zip压缩包
* 进入kwplayer/build目录
* 运行build.sh, 用于创建fakeroot目录, 需要普通用户权限;
* 运行generate_deb.sh 用于创建deb包, 由于使用了dpkg命令来打包, 这个脚本需要root权限
* 一切无误的话, 会在kwplayer/bin/目录下生成kwplayer.deb, 生成的deb包可以用dpkg命令来安装: `# dpkg -i kwplayer.deb`.

如果不想手动打包的话, 在bin/目录里面有我打包好的kwplayer.deb, 也可以直接使用.

对于Debian Wheezy, 由于gstreamer0.1(python)中不能直接把视频渲染到
DrawingArea上, 在播放MV时视频窗口被被弹出, 这个bug我暂时不没时间修复;


对于Fedora, 我专门安装并测试了Fedora 19 amd64, 也很简单, 需要这些操作:

* 更新系统. 我用的是mirrors.163.com这个更新源, 速度很好.
* 安装python3-cairo.
* 使用rpmfushion, 可以参考这篇文章:http://blog.csdn.net/sabalol/article/details/9286073
* 安装gstreamer1-libav
* 不需要安装python3-gobject或gstreamer的其它组件, 因为它们都在安装系统时自动被安装了.
* 安装leveldb 和 python3-plyvel. 

Gentoo/Arch Linux的话, 也没什么好说的, 看一下上面的依赖包, 缺少的都给装上, 
应该就能运行了. 但gentoo中稍稍注意一下软件版本的问题.


已经测试通过的发行版(版本):

* Debian sid
* Debian testing
* Debian whezy
* Ubuntu 13.10 Beta
* Ubuntu 13.04
* Ubuntu 12.10
* Ubuntu 12.04
* Gentoo
* Fedora 19
* Arch Linux


Tips & Tricks
=============
* 播放歌曲时双击左上角的歌手的头像可以在播放列表中定位正在播放的这首歌.
* 播放列表中的歌曲可以直接拖放到其它列表, 支持键盘操作, 比如Ctrl+A全选;
选择歌曲时按下Ctrl键可多选. 按Del键可以删除选中的歌曲.
* 对于小屏的笔记本来说, 全屏播放MV的效果更好.
* 尽量不下载ape格式的歌曲, 因为这种格式的文件实在太大了.


Q&A
===
问: 为什么只使用mp3(192K)和ape两种格式的音乐?

答: 其它格式都不太适用, 比如wma的音质不好; 而192K的mp3对于一般用户已经足够好了; 而对于音乐发烧友来说, 320K的mp3格式的质量仍然是很差劲的, 只有ape才能满足他(她)们的要求. 举例来说, 192K的mp3大小是4.7M, 320K的mp3是7.2M, 而对应的ape格式的是31.5M左右, 这就是差距.
总之, 这两种格式足够了.

问: 为什么不能用它来打开/管理本地的音乐?

答: 没有必要. 因为Linux桌面已经有不少强大的音乐管理软件了, 像rhythmbox, audacity, amarok等, 干嘛要加入一些重复的功能?


TODO
====
* 播放列表支持歌曲的拖放(已完成).
* 在gnome3.10中, 屏幕锁定时, 仍然能控制播放器, 比如下一曲, 暂停等.
* 加入dbus.
* 支持键盘上的多媒体键.
* 支持Debian stable (已支持)
* 为Ubuntu创建PPA (已放弃, 因为它不能保证与debian等发行版的兼容性)
* 优化歌词的显示效果(准备重写, 不再用textview来显示文本)
* 将播放列表中的音乐导出到其它目录, 也可以导出到手机中(已完成)
* 自动修复mp3的tag编码 (已完成)
* 支持打开/管理本地的多媒体资源(已放弃)
* 使用gettext国际化(i18n) (已完成)
* 加入简体中文(zh_CN.po) (已完成)
* 加入繁体中文(zh_TW.po) (已完成)
* 全屏播放(正在修复其中的一个bug)
* 实时的简体与繁体的转换, 对于使用繁体中文显示的朋友来说会非常方便, 因为显面中的简体中文会自动转为繁体来显示, 并且也可以使用繁体来搜索(已放弃)


截图
====
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

THANKS
======
`mutagenx(mutagen)` 模块来自https://github.com/LordSputnik/mutagen
这个模块被集成过来, 主要是为了方便朋友们安装, 因为debian/fedora中集成了
python2 的版本(http://code.google.com/p/mutagen). 当然了, 也可以从github
得到最新的mutagen(python3)代码, 安装也很方便.

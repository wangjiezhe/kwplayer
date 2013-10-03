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
* leveldb - 强大的NoSQL数据库(用于缓存数据);
* python3-leveldb  -  leveldb的python3绑定(Fedora中是python3-plyvel);

也可以直接运行build/下面的脚本, 生成deb包, 它会自动处理依赖关系, 不需要手动
安装上面列出的那些软件包, 需要以下的操作:

* 更新系统
* `git clone https://github.com/LiuLang/kwplayer`
* 进入kwplayer/build目录
* 运行build.sh, 用于创建fakeroot目录, 需要普通用户权限;
* 运行generate_deb.sh 用于创建deb包, 由于使用了dpkg命令来打包, 这个脚本需要root权限
* 一切无误的话, 会在kwplayer/bin/目录下生成kwplayer.deb, 生成的deb包可以用dpkg命令来安装: `# dpkg -i kwplayer.deb`.

如果不想手动打包的话, 在bin/目录里面有我打包好的kwplayer.deb, 也可以直接使用.


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
* Ubuntu 12.10
* Ubuntu 13.10 Beta
* Gentoo
* Fedora 19
* Arch Linux

已经测试失败的发行版:

* Debian wheezy (正在测试)
* Ubuntu 12.04 (软件包太旧)


Q&A
===
问: 为什么只使用mp3(192K)和ape两种格式的音乐?

答: 其它格式都不太适用, 比如wma的音质不好; 而192K的mp3对于一般用户已经足够好了; 而对于音乐发烧友来说, 320K的mp3格式的质量仍然是很差劲的, 只有ape才能满足他(她)们的要求. 举例来说, 192K的mp3大小是4.7M, 320K的mp3是7.2M, 而对应的ape格式的是31.5M左右, 这就是差距.
总之, 这两种格式足够了.

问: 为什么不能用它来打开/管理本地的音乐?

答: 没有必要. 因为Linux桌面已经有不少强大的音乐管理软件了, 像rhythmbox, audacity, amarok等, 干嘛要加入一些重复的功能?


TODO
====
* 支持Debian stable (正在测试)
* 为Ubuntu创建PPA (已放弃, 因为它不能保证与debian等发行版的兼容性)
* 优化歌词的显示效果
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

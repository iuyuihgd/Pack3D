[app]

# 应用标题
title = Pack3D

# 应用包名
package.name = pack3d
package.domain = org.github

# 源文件目录和包含的扩展名
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# 应用版本
version = 0.1

# 依赖包
requirements = python3,kivy,kivymd,py3dbp,numpy==1.24.3

# Android 配置
android.api = 33
android.ndk = 25b
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
# android.sdk 已被弃用，已移除此行
android.build_tools = 34.0.0
android.allow_backup = True
android.use_aapt2 = True

# 权限
android.permissions = INTERNET

# 修复 autoconf 问题的配置 - 使用新参数名
android.whitelist = m4_allow_all.ac
android.p4a_hooks = hooks.py

# 构建优化
android.num_processes = 4
android.logcat_filters = *:S python:D

# 图标和启动画面
icon.fg = images/icon.png
presplash.fg = images/presplash.png
presplash.background = #FFFFFF

# 日志级别
log_level = 2

# 构建目录
build.dir = bin
bin.dir = bin

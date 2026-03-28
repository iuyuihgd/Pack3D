[app]
title = Pack3D
package.name = pack3d
package.domain = org.github
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# 依赖包（建议先简化测试）
requirements = python3,kivy,kivymd,py3dbp,numpy==1.24.3

# Android 配置
android.api = 33
android.ndk = 25b
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
android.build_tools = 34.0.0
android.allow_backup = True
android.use_aapt2 = True
android.permissions = INTERNET

# 修复 autoconf 错误的关键配置
android.whitelist = m4_allow_all.ac
android.p4a_hooks = hooks.py

# 构建优化
android.num_processes = 4
android.logcat_filters = *:S python:D

# 日志级别
log_level = 2

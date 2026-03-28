[app]
title = Pack3D
package.name = pack3d
package.domain = org.github
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

requirements = python3,kivy,kivymd,py3dbp,numpy

android.api = 33
android.ndk = 25b
android.sdk = 24
android.arch = arm64-v8a,armeabi-v7a

android.permissions = INTERNET
android.use_aapt2 = True
android.allow_backup = True
android.logcat_filters = *:S python:D

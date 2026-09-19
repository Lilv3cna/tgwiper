[app]
title = TG Wiper
package.name = tgwiper
package.domain = org.tgwiper
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3==3.12.9,kivy==2.3.0,telethon,pyaes,rsa,pyasn1

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1

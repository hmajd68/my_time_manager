@echo off
echo ========================================
echo Building APK with Flet...
echo ========================================

REM تنظیم مسیر جاوا
set JAVA_HOME=C:\Program Files\Java\jdk-26.0.2
set PATH=%JAVA_HOME%\bin;%PATH%

REM تنظیم مسیر Flutter
set FLUTTER_ROOT=F:\flutter
set PATH=%FLUTTER_ROOT%\bin;%PATH%

REM تنظیم مسیر Android SDK
set ANDROID_HOME=C:\Users\hafez\AppData\Local\Android\Sdk
set ANDROID_SDK_ROOT=C:\Users\hafez\AppData\Local\Android\Sdk

REM مسیر cmdline-tools
set PATH=%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\tools;%ANDROID_HOME%\tools\bin;%PATH%

REM تنظیم آینه‌ها
set FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
set PUB_HOSTED_URL=https://pub.flutter-io.cn

REM ⭐ مهم: به Flet بگو از SDK موجود استفاده کند
set FLET_ANDROID_SDK_PATH=%ANDROID_HOME%

echo ========================================
echo Checking installations...
echo ========================================
java --version
flutter --version

echo ========================================
echo Building APK...
echo ========================================

flet build apk

pause
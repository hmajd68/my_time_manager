@echo off
echo ========================================
echo Setting up Flutter and Android SDK...
echo ========================================

REM تنظیم مسیر Flutter
set FLUTTER_ROOT=F:\flutter
set PATH=%FLUTTER_ROOT%\bin;%PATH%

REM تنظیم مسیر Android SDK
set ANDROID_HOME=C:\Users\hafez\AppData\Local\Android\Sdk
set ANDROID_SDK_ROOT=C:\Users\hafez\AppData\Local\Android\Sdk

REM اضافه کردن مسیر SDK به PATH
set PATH=%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\tools;%ANDROID_HOME%\tools\bin;%PATH%

REM تنظیم آینه‌ها
set FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
set PUB_HOSTED_URL=https://pub.flutter-io.cn

REM ⭐ مهم: به Flet بگو از SDK موجود استفاده کند و چیزی نصب نکند
set FLET_BUILD_USE_EXISTING_SDK=1
set SKIP_JDK_VERSION_CHECK=true
set FLET_ANDROID_SDK_PATH=C:\Users\hafez\AppData\Local\Android\Sdk

echo Checking Flutter installation...
flutter --version

echo ========================================
echo Building APK...
echo ========================================

flet build apk --verbose

pause
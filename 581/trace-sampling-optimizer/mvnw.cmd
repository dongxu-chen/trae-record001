@REM Maven Wrapper startup batch script
@REM This script downloads Maven if not present and runs the build

@echo off
setlocal

set MAVEN_VERSION=3.9.6
set MAVEN_URL=https://mirrors.aliyun.com/apache/maven/apache-maven/%MAVEN_VERSION%/apache-maven-%MAVEN_VERSION%-bin.zip
set MAVEN_HOME=%~dp0.mvn\maven\apache-maven-%MAVEN_VERSION%

if exist "%MAVEN_HOME%\bin\mvn.cmd" goto runMaven

echo Maven not found, downloading Maven %MAVEN_VERSION%...
mkdir "%MAVEN_HOME%" 2>nul

powershell -Command "& {Invoke-WebRequest -Uri '%MAVEN_URL%' -OutFile '%~dp0.mvn\maven.zip'; Expand-Archive -Path '%~dp0.mvn\maven.zip' -DestinationPath '%~dp0.mvn\maven' -Force}" 2>nul
if errorlevel 1 (
    echo Trying backup mirror...
    set MAVEN_URL=https://mirrors.huaweicloud.com/apache/maven/maven-3/%MAVEN_VERSION%/binaries/apache-maven-%MAVEN_VERSION%-bin.zip
    powershell -Command "& {Invoke-WebRequest -Uri '%MAVEN_URL%' -OutFile '%~dp0.mvn\maven.zip'; Expand-Archive -Path '%~dp0.mvn\maven.zip' -DestinationPath '%~dp0.mvn\maven' -Force}"
)

:runMaven
"%MAVEN_HOME%\bin\mvn.cmd" %*

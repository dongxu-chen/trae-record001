@echo off
setlocal

set "DIRNAME=%~dp0"
if "%DIRNAME%" == "" set "DIRNAME=."

set "APP_HOME=%DIRNAME%"
set "WRAPPER_JAR=%APP_HOME%\.mvn\wrapper\maven-wrapper.jar"

if not exist "%WRAPPER_JAR%" (
  echo Maven Wrapper JAR not found. Please download it to .mvn/wrapper/maven-wrapper.jar
  exit /b 1
)

set "JAVA_EXE=java"
if defined JAVA_HOME (
  set "JAVA_EXE=%JAVA_HOME%\bin\java.exe"
)

"%JAVA_EXE%" -classpath "%WRAPPER_JAR%" org.apache.maven.wrapper.MavenWrapperMain %*

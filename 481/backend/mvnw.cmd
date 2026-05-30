@echo off
set ERROR_CODE=0

set MAVEN_PROJECTBASEDIR=%~dp0..

set WRAPPER_JAR="%MAVEN_PROJECTBASEDIR%\.mvn\wrapper\maven-wrapper.jar"
set WRAPPER_LAUNCHER=org.apache.maven.wrapper.MavenWrapperMain

if not exist %WRAPPER_JAR% (
    echo Downloading Maven Wrapper...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://repo.maven.apache.org/maven2/org/apache/maven/wrapper/maven-wrapper/3.2.0/maven-wrapper-3.2.0.jar' -OutFile %WRAPPER_JAR%"
)

set JAVA_EXE=java
if defined JAVA_HOME set JAVA_EXE="%JAVA_HOME%\bin\java.exe"

%JAVA_EXE% %MAVEN_OPTS% -classpath %WRAPPER_JAR% %WRAPPER_LAUNCHER% %*
if ERRORLEVEL 1 goto error
goto end

:error
set ERROR_CODE=1

:end
exit /B %ERROR_CODE%

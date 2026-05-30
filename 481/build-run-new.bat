@echo off
cd /d d:\Trae\project\record001\481\backend
del d:\Trae\maven-build.log
echo Starting Maven build at %date% %time% > d:\Trae\maven-build.log
java -Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain clean compile >> d:\Trae\maven-build.log 2>&1
echo Build exit code: %errorlevel% >> d:\Trae\maven-build.log
if %errorlevel% neq 0 (
    echo Build failed, exiting. >> d:\Trae\maven-build.log
    exit /b %errorlevel%
)
echo. >> d:\Trae\maven-build.log
echo Starting Spring Boot at %date% %time% >> d:\Trae\maven-build.log
java -Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain spring-boot:run >> d:\Trae\maven-build.log 2>&1
echo Run exit code: %errorlevel% >> d:\Trae\maven-build.log

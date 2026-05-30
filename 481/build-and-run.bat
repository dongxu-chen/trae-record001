@echo off
cd /d d:\Trae\project\record001\481\backend
echo Starting Maven build... > d:\Trae\maven-build.log
java -Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain clean compile >> d:\Trae\maven-build.log 2>&1
echo Build exit code: %errorlevel% >> d:\Trae\maven-build.log
echo. >> d:\Trae\maven-build.log
echo Starting Spring Boot... >> d:\Trae\maven-build.log
java -Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain spring-boot:run >> d:\Trae\maven-build.log 2>&1
echo Run exit code: %errorlevel% >> d:\Trae\maven-build.log

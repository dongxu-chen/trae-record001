@echo off
cd /d d:\Trae\project\record001\481\backend
java -Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain spring-boot:run > d:\Trae\project\record001\481\backend.log 2>&1

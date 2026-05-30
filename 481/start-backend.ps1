$ErrorActionPreference = "Continue"
Set-Location "d:\Trae\project\record001\481\backend"
$process = Start-Process java -ArgumentList @(
    "-Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend",
    "-classpath", ".mvn\wrapper\maven-wrapper.jar",
    "org.apache.maven.wrapper.MavenWrapperMain",
    "spring-boot:run"
) -PassThru -NoNewWindow -RedirectStandardOutput "d:\Trae\backend.log" -RedirectStandardError "d:\Trae\backend-error.log"
Write-Host "Process started with PID: $process.Id"

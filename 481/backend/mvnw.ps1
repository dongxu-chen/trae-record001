$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wrapperJar = Join-Path $projectDir ".mvn\wrapper\maven-wrapper.jar"

if (-not (Test-Path $wrapperJar)) {
    Write-Host "Downloading Maven Wrapper..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri "https://repo.maven.apache.org/maven2/org/apache/maven/wrapper/maven-wrapper/3.2.0/maven-wrapper-3.2.0.jar" -OutFile $wrapperJar
}

$javaExe = "java"
if ($env:JAVA_HOME) {
    $javaExe = Join-Path $env:JAVA_HOME "bin\java.exe"
}

$allArgs = $args -join " "

& $javaExe "-Dmaven.multiModuleProjectDirectory=$projectDir" -classpath $wrapperJar org.apache.maven.wrapper.MavenWrapperMain $allArgs

$ErrorActionPreference = "Continue"
Set-Location "d:\Trae\project\record001\481\backend"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "java"
$psi.Arguments = "-Dmaven.multiModuleProjectDirectory=d:\Trae\project\record001\481\backend -classpath .mvn\wrapper\maven-wrapper.jar org.apache.maven.wrapper.MavenWrapperMain spring-boot:run"
$psi.WorkingDirectory = "d:\Trae\project\record001\481\backend"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$process.Start() | Out-Null

$output = $process.StandardOutput.ReadToEnd()
$error = $process.StandardError.ReadToEnd()
$process.WaitForExit()

$output | Out-File -FilePath "d:\Trae\full-output.log" -Encoding UTF8
$error | Out-File -FilePath "d:\Trae\full-error.log" -Encoding UTF8

Write-Host "Exit code: $($process.ExitCode)"
Write-Host "Output written to d:\Trae\full-output.log"
Write-Host "Error written to d:\Trae\full-error.log"

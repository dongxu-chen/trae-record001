import times, strformat, locks

var
  logLock: Lock

proc initLogger*() =
  initLock(logLock)

proc logMessage*(level: LogLevel, message: string) =
  let timestamp = getTime().format("yyyy-MM-dd HH:mm:ss")
  let levelStr = case level
    of DEBUG: "DEBUG"
    of INFO: "INFO"
    of WARN: "WARN"
    of ERROR: "ERROR"
  
  let logLine = fmt"[{timestamp}] [{levelStr}] {message}"
  
  withLock logLock:
    echo logLine
    flushFile(stdout)

proc debug*(message: string) = logMessage(DEBUG, message)
proc info*(message: string) = logMessage(INFO, message)
proc warn*(message: string) = logMessage(WARN, message)
proc error*(message: string) = logMessage(ERROR, message)
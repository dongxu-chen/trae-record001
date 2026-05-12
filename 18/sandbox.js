const Docker = require('dockerode');
const path = require('path');
const fs = require('fs');
const os = require('os');

const docker = new Docker();
const TIMEOUT = 15000;
const MEMORY_LIMIT = 512 * 1024 * 1024;
const CPU_LIMIT = 2;
const CLEANUP_INTERVAL = 30000;

const LANGUAGE_CONFIG = {
  javascript: {
    image: 'node:18-alpine',
    filename: 'index.js',
    cmd: ['node', '/sandbox/index.js'],
    wrapCode: (code) => `
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info
};

const output = [];

const captureOutput = (level) => (...args) => {
  const message = args.map(arg => {
    if (typeof arg === 'object') {
      try {
        return JSON.stringify(arg, null, 2);
      } catch (e) {
        return String(arg);
      }
    }
    return String(arg);
  }).join(' ');
  
  output.push({
    level,
    message,
    timestamp: new Date().toISOString()
  });
  
  originalConsole[level](...args);
};

console.log = captureOutput('log');
console.error = captureOutput('error');
console.warn = captureOutput('warn');
console.info = captureOutput('info');

process.on('uncaughtException', (error) => {
  console.error('未捕获异常:', error.message);
  console.error('堆栈:', error.stack);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('未处理的 Promise 拒绝:', String(reason));
  process.exit(1);
});

try {
${code}
} catch (error) {
  console.error('运行时错误:', error.message);
  console.error('堆栈:', error.stack);
  process.exit(1);
}

process.on('exit', () => {
  console.log('__SANDBOX_OUTPUT__:' + JSON.stringify(output));
});
`,
    timeout: 10000
  },
  python: {
    image: 'python:3.11-alpine',
    filename: 'main.py',
    cmd: ['python3', '/sandbox/main.py'],
    wrapCode: (code) => `
import sys
import json
import traceback
from datetime import datetime, timezone

output = []

def capture_output(level):
    def wrapper(*args):
        nonlocal output
        messages = []
        for arg in args:
            try:
                if isinstance(arg, (dict, list, tuple)):
                    messages.append(json.dumps(arg, ensure_ascii=False, indent=2))
                else:
                    messages.append(str(arg))
            except:
                messages.append(str(arg))
        
        message = ' '.join(messages)
        output.append({
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        orig_print = globals().get('_orig_print', print)
        orig_print(*args)
    return wrapper

_orig_print = print
print = capture_output('log')

def print_error(*args):
    capture_output('error')(*args)

def print_warn(*args):
    capture_output('warn')(*args)

def print_info(*args):
    capture_output('info')(*args)

try:
    exec('''
${code}
''')
except SystemExit:
    pass
except Exception as e:
    print_error('运行时错误:', str(e))
    print_error('堆栈:')
    tb_lines = traceback.format_exc().split('\\n')
    for line in tb_lines:
        if line:
            print_error(line)
    sys.exit(1)
finally:
    print('__SANDBOX_OUTPUT__:' + json.dumps(output, ensure_ascii=False))
`,
    timeout: 15000
  },
  java: {
    image: 'openjdk:17-alpine',
    filename: 'Main.java',
    cmd: ['sh', '-c', 'cd /sandbox && javac Main.java && java Main'],
    wrapCode: (code) => `
import java.util.*;
import java.io.*;
import java.time.*;
import java.time.format.*;

public class Main {
    public static List<OutputEntry> output = new ArrayList<>();
    
    public static class OutputEntry {
        String level;
        String message;
        String timestamp;
        
        public OutputEntry(String level, String message) {
            this.level = level;
            this.message = message;
            this.timestamp = Instant.now().toString();
        }
        
        public String toJson() {
            return "{\\\"level\\\":\\\"" + level + "\\\",\\\"message\\\":\\\"" + 
                   message.replace("\\\\", "\\\\\\\\").replace("\\\"", "\\\\\\\"") + 
                   "\\\",\\\"timestamp\\\":\\\"" + timestamp + "\\\"}";
        }
    }
    
    public static void log(String level, Object... args) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < args.length; i++) {
            if (i > 0) sb.append(" ");
            if (args[i] == null) {
                sb.append("null");
            } else {
                try {
                    if (args[i].getClass().isArray()) {
                        sb.append(Arrays.deepToString((Object[]) args[i]));
                    } else {
                        sb.append(args[i].toString());
                    }
                } catch (Exception e) {
                    sb.append(String.valueOf(args[i]));
                }
            }
        }
        output.add(new OutputEntry(level, sb.toString()));
        System.out.println(sb.toString());
    }
    
    public static void main(String[] args) {
        try {
${code}
        } catch (Exception e) {
            log("error", "运行时错误:", e.getMessage());
            log("error", "堆栈:");
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            for (String line : sw.toString().split("\\n")) {
                if (!line.isEmpty()) {
                    log("error", line);
                }
            }
            System.exit(1);
        } finally {
            StringBuilder json = new StringBuilder("[");
            for (int i = 0; i < output.size(); i++) {
                if (i > 0) json.append(",");
                json.append(output.get(i).toJson());
            }
            json.append("]");
            System.out.println("__SANDBOX_OUTPUT__:" + json.toString());
        }
    }
}
`,
    timeout: 20000
  },
  go: {
    image: 'golang:1.21-alpine',
    filename: 'main.go',
    cmd: ['sh', '-c', 'cd /sandbox && go run main.go'],
    wrapCode: (code) => `
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"runtime/debug"
	"time"
)

type OutputEntry struct {
	Level     string ` + "`json:\"level\"`" + `
	Message   string ` + "`json:\"message\"`" + `
	Timestamp string ` + "`json:\"timestamp\"`" + `
}

var output []OutputEntry

func captureOutput(level string, args ...interface{}) {
	var msg string
	if len(args) == 1 {
		if str, ok := args[0].(string); ok {
			msg = str
		} else {
			data, err := json.MarshalIndent(args[0], "", "  ")
			if err == nil {
				msg = string(data)
			} else {
				msg = fmt.Sprintf("%v", args[0])
			}
		}
	} else {
		msg = fmt.Sprint(args...)
	}
	
	output = append(output, OutputEntry{
		Level:     level,
		Message:   msg,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
	})
	
	fmt.Println(msg)
}

func main() {
	defer func() {
		if r := recover(); r != nil {
			captureOutput("error", "运行时错误:", fmt.Sprint(r))
			captureOutput("error", "堆栈:")
			for _, line := range string(debug.Stack()) {
				if string(line) != "\n" {
					captureOutput("error", string(line))
				}
			}
			printOutput()
			os.Exit(1)
		}
		printOutput()
	}()

${code}
}

func printOutput() {
	data, err := json.Marshal(output)
	if err == nil {
		fmt.Println("__SANDBOX_OUTPUT__:" + string(data))
	}
}
`,
    timeout: 20000
  }
};

const activeContainers = new Map();
const imagePromises = new Map();
let cleanupInterval = null;

function getSupportedLanguages() {
  return Object.keys(LANGUAGE_CONFIG);
}

function startCleanupService() {
  if (cleanupInterval) return;

  cleanupInterval = setInterval(async () => {
    const now = Date.now();
    const toCleanup = [];

    for (const [containerId, info] of activeContainers.entries()) {
      const timeout = LANGUAGE_CONFIG[info.language]?.timeout || TIMEOUT;
      if (now - info.createdAt > timeout * 2) {
        toCleanup.push({ containerId, ...info });
      }
    }

    for (const item of toCleanup) {
      try {
        await cleanupContainer(item.containerId);
        activeContainers.delete(item.containerId);
        console.log(`[清理服务] 容器 ${item.containerId.slice(0, 12)} 已清理`);
      } catch (error) {
        console.error(`[清理服务] 清理容器 ${item.containerId.slice(0, 12)} 失败:`, error.message);
      }
    }

    if (toCleanup.length > 0) {
      console.log(`[清理服务] 本轮清理 ${toCleanup.length} 个过期容器`);
    }
  }, CLEANUP_INTERVAL);
}

function stopCleanupService() {
  if (cleanupInterval) {
    clearInterval(cleanupInterval);
    cleanupInterval = null;
  }
}

async function cleanupContainer(containerId) {
  try {
    const container = docker.getContainer(containerId);

    try {
      await container.inspect();
    } catch (error) {
      return;
    }

    try {
      await container.stop({ t: 2 });
    } catch (error) {
      if (!error.message.includes('is not running')) {
        console.warn(`停止容器 ${containerId.slice(0, 12)} 失败:`, error.message);
      }
    }

    try {
      await container.remove({ force: true, v: true });
    } catch (error) {
      if (!error.message.includes('No such container')) {
        console.warn(`删除容器 ${containerId.slice(0, 12)} 失败:`, error.message);
      }
    }
  } catch (error) {
    console.error(`清理容器 ${containerId.slice(0, 12)} 异常:`, error.message);
  }
}

async function cleanupAllContainers() {
  const containers = await docker.listContainers({ all: true });
  
  const sandboxImages = Object.values(LANGUAGE_CONFIG).map(c => c.image);
  const sandboxContainers = containers.filter((c) => {
    const name = c.Names?.[0] || '';
    const image = c.Image || '';
    return sandboxImages.some(img => image.includes(img.split(':')[0])) || name.includes('sandbox');
  });

  for (const containerInfo of sandboxContainers) {
    await cleanupContainer(containerInfo.Id);
  }
}

async function ensureImage(imageName) {
  if (imagePromises.has(imageName)) {
    return imagePromises.get(imageName);
  }

  const promise = (async () => {
    try {
      await docker.getImage(imageName).inspect();
      return true;
    } catch (error) {
      console.log(`正在拉取镜像 ${imageName}...`);
      await new Promise((resolve, reject) => {
        docker.pull(imageName, (err, stream) => {
          if (err) return reject(err);
          docker.modem.followProgress(stream, (err, output) => {
            if (err) return reject(err);
            resolve(output);
          });
        });
      });
      console.log(`镜像 ${imageName} 拉取完成`);
      return true;
    }
  })();

  imagePromises.set(imageName, promise);
  return promise;
}

async function executeCode(code, executionId, language = 'javascript') {
  if (!LANGUAGE_CONFIG[language]) {
    throw new Error(`不支持的语言: ${language}`);
  }

  const config = LANGUAGE_CONFIG[language];
  const timeout = config.timeout || TIMEOUT;

  startCleanupService();

  const startTime = Date.now();
  let container = null;
  let containerId = null;
  let tempDir = null;
  let logStream = null;
  let timeoutTimer = null;
  let isCleanedUp = false;

  const cleanup = async () => {
    if (isCleanedUp) return;
    isCleanedUp = true;

    if (timeoutTimer) {
      clearTimeout(timeoutTimer);
      timeoutTimer = null;
    }

    if (logStream) {
      try {
        logStream.destroy();
      } catch (e) {}
      logStream = null;
    }

    if (containerId) {
      activeContainers.delete(containerId);
      await cleanupContainer(containerId);
      containerId = null;
    }

    if (tempDir && fs.existsSync(tempDir)) {
      try {
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch (e) {
        console.error('清理临时目录失败:', e.message);
      }
      tempDir = null;
    }
  };

  try {
    await ensureImage(config.image);

    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), `sandbox-${executionId}-`));
    const codeFile = path.join(tempDir, config.filename);
    const wrappedCode = config.wrapCode(code);
    fs.writeFileSync(codeFile, wrappedCode, 'utf8');

    const containerConfig = {
      Image: config.image,
      Cmd: config.cmd,
      AttachStdout: true,
      AttachStderr: true,
      Tty: false,
      HostConfig: {
        Binds: [`${tempDir}:/sandbox:ro`],
        Memory: MEMORY_LIMIT,
        MemorySwap: MEMORY_LIMIT,
        CpuPeriod: 100000,
        CpuQuota: CPU_LIMIT * 100000,
        NetworkMode: 'none',
        ReadonlyRootfs: true,
        CapDrop: ['ALL'],
        SecurityOpt: ['no-new-privileges'],
        AutoRemove: false
      },
      Env: ['NODE_ENV=production', 'PYTHONDONTWRITEBYTECODE=1']
    };

    console.log(`[${executionId}] 创建 ${language} 容器`);
    container = await docker.createContainer(containerConfig);
    containerId = container.id;

    activeContainers.set(containerId, {
      executionId,
      language,
      createdAt: Date.now(),
      tempDir
    });

    console.log(`[${executionId}] 启动容器 (${containerId.slice(0, 12)})`);
    await container.start();

    let stdout = '';
    let stderr = '';

    const executionPromise = new Promise((resolve, reject) => {
      let waitResult = null;
      let logsResolved = false;
      let waitResolved = false;

      const tryResolve = () => {
        if (logsResolved && waitResolved) {
          resolve(waitResult);
        }
      };

      container.logs({
        follow: true,
        stdout: true,
        stderr: true,
        stream: true
      }).then((stream) => {
        logStream = stream;

        stream.on('data', (data) => {
          stdout += data.toString();
        });

        stream.on('error', (err) => {
          reject(err);
        });

        stream.on('end', () => {
          logsResolved = true;
          tryResolve();
        });

        stream.on('close', () => {
          logsResolved = true;
          tryResolve();
        });
      }).catch(reject);

      container.wait().then((result) => {
        waitResult = result;
        waitResolved = true;
        tryResolve();
      }).catch(reject);
    });

    const timeoutPromise = new Promise((_, reject) => {
      timeoutTimer = setTimeout(() => {
        reject(new Error(`执行超时（${timeout / 1000}秒）`));
      }, timeout);
    });

    const result = await Promise.race([executionPromise, timeoutPromise]);

    const outputMatch = stdout.match(/__SANDBOX_OUTPUT__:(\[.*\])$/m);
    let parsedOutput = [];
    let error = null;

    if (outputMatch) {
      try {
        parsedOutput = JSON.parse(outputMatch[1]);
      } catch (e) {
        console.error('解析输出失败:', e.message);
      }
    }

    if (result && result.StatusCode !== 0) {
      if (stderr) {
        parsedOutput.push({
          level: 'error',
          message: stderr,
          timestamp: new Date().toISOString()
        });
      } else {
        error = '执行失败';
      }
    }

    const duration = Date.now() - startTime;

    await cleanup();

    return {
      output: parsedOutput,
      error,
      duration,
      exitCode: result ? result.StatusCode : 0,
      language
    };
  } catch (error) {
    await cleanup();
    throw error;
  } finally {
    await cleanup();
  }
}

process.on('SIGINT', async () => {
  console.log('\n正在关闭沙箱服务...');
  stopCleanupService();
  await cleanupAllContainers();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n收到终止信号，清理资源...');
  stopCleanupService();
  await cleanupAllContainers();
  process.exit(0);
});

process.on('exit', () => {
  stopCleanupService();
});

process.on('uncaughtException', (error) => {
  console.error('沙箱未捕获异常:', error);
  stopCleanupService();
});

module.exports = {
  executeCode,
  cleanupAllContainers,
  startCleanupService,
  stopCleanupService,
  getSupportedLanguages,
  LANGUAGE_CONFIG
};

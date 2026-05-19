import subprocess
import tempfile
import os
import sys
import signal
from datetime import datetime
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def kill_process_tree(pid: int):
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                          capture_output=True, timeout=5)
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception as e:
        logger.warning(f"Failed to kill process {pid}: {e}")


class TaskExecutor:
    @staticmethod
    def execute_shell_script(script_content: str, timeout: int = 300) -> Tuple[str, Optional[str], int]:
        start_time = datetime.now()
        temp_file = None
        process = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.bat' if os.name == 'nt' else '.sh', delete=False) as f:
                f.write(script_content)
                temp_file = f.name

            if os.name != 'nt':
                os.chmod(temp_file, 0o755)

            cmd = [temp_file] if os.name == 'nt' else ['bash', temp_file]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True if os.name == 'nt' else False,
                preexec_fn=None if os.name == 'nt' else os.setsid
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(process.pid)
                process.wait(timeout=5)
                execution_time = int((datetime.now() - start_time).total_seconds())
                return "", f"Script timed out after {timeout} seconds and was terminated", execution_time

            execution_time = int((datetime.now() - start_time).total_seconds())

            if process.returncode == 0:
                return stdout, None, execution_time
            else:
                return stdout, stderr, execution_time

        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds())
            return "", str(e), execution_time
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

    @staticmethod
    def execute_python_script(script_content: str, timeout: int = 300) -> Tuple[str, Optional[str], int]:
        start_time = datetime.now()
        temp_file = None
        process = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_file = f.name

            process = subprocess.Popen(
                [sys.executable, temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=None if os.name == 'nt' else os.setsid
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(process.pid)
                process.wait(timeout=5)
                execution_time = int((datetime.now() - start_time).total_seconds())
                return "", f"Script timed out after {timeout} seconds and was terminated", execution_time

            execution_time = int((datetime.now() - start_time).total_seconds())

            if process.returncode == 0:
                return stdout, None, execution_time
            else:
                return stdout, stderr, execution_time

        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds())
            return "", str(e), execution_time
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

    @classmethod
    def execute_task(cls, task_type: str, script_content: str, timeout: int = 300) -> Tuple[str, Optional[str], int]:
        logger.info(f"Executing {task_type} task with timeout {timeout}s")

        if task_type == 'shell':
            return cls.execute_shell_script(script_content, timeout)
        elif task_type == 'python':
            return cls.execute_python_script(script_content, timeout)
        else:
            return "", f"Unknown task type: {task_type}", 0
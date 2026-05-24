import json
import subprocess
import logging
import tempfile
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AnsibleRunner:
    def __init__(self, inventory_path: Optional[str] = None):
        self.inventory_path = inventory_path

    def generate_inventory(self, hosts: List[Dict]) -> str:
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False)
        inventory_content = "[baseline_check]\n"
        for host in hosts:
            hostname = host.get("hostname")
            port = host.get("port", 22)
            username = host.get("username", "root")
            password = host.get("password", "")
            key_file = host.get("key_file", "")

            line = f"{hostname} ansible_port={port} ansible_user={username}"
            if password:
                line += f" ansible_password={password}"
            if key_file:
                line += f" ansible_ssh_private_key_file={key_file}"
            line += " ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n"
            inventory_content += line

        temp_file.write(inventory_content)
        temp_file.close()
        return temp_file.name

    def generate_playbook(self, checks: List[Dict], output_dir: str) -> str:
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)

        playbook = [
            {
                "name": "Baseline Check",
                "hosts": "baseline_check",
                "gather_facts": True,
                "tasks": []
            }
        ]

        for check in checks:
            task = self._check_to_task(check)
            if task:
                playbook[0]["tasks"].append(task)

        import yaml
        yaml.dump(playbook, temp_file, default_flow_style=False, allow_unicode=True)
        temp_file.close()
        return temp_file.name

    def _check_to_task(self, check: Dict) -> Optional[Dict]:
        check_type = check.get("check_type")
        task_id = check.get("id")
        task_name = check.get("name")

        if check_type == "file_content":
            return {
                "name": f"Check {task_id}: {task_name}",
                "ansible.builtin.shell": f"grep -E '{check.get('pattern')}' {check.get('file_path')} || true",
                "register": f"result_{task_id.replace('-', '_')}",
                "changed_when": False
            }
        elif check_type == "sysctl":
            return {
                "name": f"Check {task_id}: {task_name}",
                "ansible.builtin.shell": f"sysctl -n {check.get('parameter')} || true",
                "register": f"result_{task_id.replace('-', '_')}",
                "changed_when": False
            }
        elif check_type == "file_permission":
            return {
                "name": f"Check {task_id}: {task_name}",
                "ansible.builtin.stat":
                    {"path": check.get("file_path")},
                "register": f"result_{task_id.replace('-', '_')}",
                "changed_when": False
            }
        elif check_type == "command":
            return {
                "name": f"Check {task_id}: {task_name}",
                "ansible.builtin.shell": check.get("command"),
                "register": f"result_{task_id.replace('-', '_')}",
                "changed_when": False
            }
        elif check_type == "service_status":
            return {
                "name": f"Check {task_id}: {task_name}",
                "ansible.builtin.systemd":
                    {"name": check.get("service_name")},
                "register": f"result_{task_id.replace('-', '_')}",
                "changed_when": False,
                "ignore_errors": True
            }

        return None

    def run_playbook(self, playbook_path: str, inventory_path: str) -> Dict:
        cmd = [
            "ansible-playbook",
            "-i", inventory_path,
            playbook_path,
            "--forks", "10",
            "-v"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            logger.error(f"Ansible playbook execution failed: {str(e)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def apply_fix(self, host: Dict, fix_command: str) -> Dict:
        inventory = self.generate_inventory([host])

        playbook_content = [
            {
                "name": "Apply Fix",
                "hosts": "baseline_check",
                "tasks": [
                    {
                        "name": "Execute fix command",
                        "ansible.builtin.shell": fix_command,
                        "become": True
                    }
                ]
            }
        ]

        import yaml
        playbook_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        yaml.dump(playbook_content, playbook_file, default_flow_style=False)
        playbook_file.close()

        result = self.run_playbook(playbook_file.name, inventory)

        os.unlink(inventory)
        os.unlink(playbook_file.name)

        return result

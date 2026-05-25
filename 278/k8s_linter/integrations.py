import subprocess
import shutil
from pathlib import Path
from typing import Optional
from .detector import Report, Issue, Severity


class YamllintIntegration:
    def __init__(self):
        self.available = shutil.which('yamllint') is not None

    def run(self, file_path: str, report: Report) -> Report:
        if not self.available:
            return report

        try:
            result = subprocess.run(
                ['yamllint', '-f', 'parsable', file_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(' ', 2)
                        if len(parts) >= 3:
                            file_info = parts[0]
                            severity = parts[1]
                            message = parts[2] if len(parts) > 2 else ''

                            sev_map = {
                                'error': Severity.ERROR,
                                'warning': Severity.WARNING
                            }

                            report.add_issue(Issue(
                                rule_id=f"yamllint.{message.split('[')[1].split(']')[0] if '[' in message else 'yamllint',
                                severity=sev_map.get(severity, Severity.INFO),
                                message=f"YAML格式问题: {message}",
                                suggestion="请检查YAML格式",
                                file_path=file_path
                            ))
        except Exception:
            pass

        return report


class KubeScoreIntegration:
    def __init__(self):
        self.available = shutil.which('kube-score') is not None

    def run(self, file_path: str, report: Report) -> Report:
        if not self.available:
            return report

        try:
            result = subprocess.run(
                ['kube-score', 'score', file_path, '--output-format', 'json'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0 and result.stderr:
                pass

            if result.stdout:
                    import json
                    try:
                        data = json.loads(result.stdout)
                        for item in data:
                            for check in item.get('checks', []):
                                if check.get('grade', 10) < 10:
                                    report.add_issue(Issue(
                                        rule_id=f"kube-score.{check.get('id', 'unknown')}",
                                        severity=Severity.WARNING,
                                        message=f"kube-score: {check.get('name', '')} - {check.get('comment', '')}",
                                        suggestion=check.get('comment', ''),
                                        file_path=file_path,
                                        resource_type=item.get('type_meta', {}).get('kind', ''),
                                        resource_name=item.get('object_meta', {}).get('name', '')
                                    ))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        return report

import difflib
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    ADDED = 'added'
    REMOVED = 'removed'
    MODIFIED = 'modified'
    UNCHANGED = 'unchanged'


@dataclass
class DiffLine:
    line_number: int
    content: str
    change_type: ChangeType
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None


@dataclass
class DiffResult:
    old_content: str
    new_content: str
    lines: List[DiffLine]
    stats: Dict[str, int]
    has_changes: bool


class DiffTool:
    @staticmethod
    def compare_text(old_text: str, new_text: str, 
                    context_lines: int = 3) -> DiffResult:
        old_lines = old_text.splitlines(keepends=True) if old_text else []
        new_lines = new_text.splitlines(keepends=True) if new_text else []
        
        differ = difflib.unified_diff(
            old_lines, new_lines,
            fromfile='before',
            tofile='after',
            n=context_lines
        )
        
        diff_lines = list(differ)
        
        lines = []
        old_line_num = 1
        new_line_num = 1
        
        for line in diff_lines:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                continue
            
            if line.startswith('-'):
                lines.append(DiffLine(
                    line_number=old_line_num,
                    content=line[1:].rstrip('\n'),
                    change_type=ChangeType.REMOVED,
                    old_line_number=old_line_num
                ))
                old_line_num += 1
            elif line.startswith('+'):
                lines.append(DiffLine(
                    line_number=new_line_num,
                    content=line[1:].rstrip('\n'),
                    change_type=ChangeType.ADDED,
                    new_line_number=new_line_num
                ))
                new_line_num += 1
            else:
                lines.append(DiffLine(
                    line_number=old_line_num,
                    content=line.rstrip('\n'),
                    change_type=ChangeType.UNCHANGED,
                    old_line_number=old_line_num,
                    new_line_number=new_line_num
                ))
                old_line_num += 1
                new_line_num += 1
        
        added = sum(1 for l in lines if l.change_type == ChangeType.ADDED)
        removed = sum(1 for l in lines if l.change_type == ChangeType.REMOVED)
        unchanged = sum(1 for l in lines if l.change_type == ChangeType.UNCHANGED)
        
        return DiffResult(
            old_content=old_text,
            new_content=new_text,
            lines=lines,
            stats={
                'added': added,
                'removed': removed,
                'unchanged': unchanged,
                'total': len(lines)
            },
            has_changes=added > 0 or removed > 0
        )

    @staticmethod
    def compare_dict(old_dict: Dict, new_dict: Dict) -> Dict[str, Any]:
        all_keys = set(old_dict.keys()) | set(new_dict.keys())
        changes = {}
        
        for key in all_keys:
            old_val = old_dict.get(key)
            new_val = new_dict.get(key)
            
            if key not in old_dict:
                changes[key] = {
                    'type': 'added',
                    'new_value': new_val
                }
            elif key not in new_dict:
                changes[key] = {
                    'type': 'removed',
                    'old_value': old_val
                }
            elif old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested_changes = DiffTool.compare_dict(old_val, new_val)
                    if nested_changes:
                        changes[key] = {
                            'type': 'modified',
                            'changes': nested_changes
                        }
                elif isinstance(old_val, list) and isinstance(new_val, list):
                    changes[key] = {
                        'type': 'modified',
                        'old_value': old_val,
                        'new_value': new_val,
                        'diff': DiffTool.compare_lists(old_val, new_val)
                    }
                else:
                    changes[key] = {
                        'type': 'modified',
                        'old_value': old_val,
                        'new_value': new_val
                    }
        
        return changes

    @staticmethod
    def compare_lists(old_list: List, new_list: List) -> Dict[str, Any]:
        old_set = set(old_list)
        new_set = set(new_list)
        
        return {
            'added': list(new_set - old_set),
            'removed': list(old_set - new_set),
            'common': list(old_set & new_set)
        }

    @staticmethod
    def format_diff_html(diff_result: DiffResult) -> str:
        html_lines = []
        html_lines.append('<div class="diff-container">')
        html_lines.append('<table class="diff-table">')
        
        for line in diff_result.lines:
            css_class = {
                ChangeType.ADDED: 'diff-added',
                ChangeType.REMOVED: 'diff-removed',
                ChangeType.UNCHANGED: 'diff-unchanged'
            }.get(line.change_type, '')
            
            old_num = line.old_line_number or '&nbsp;'
            new_num = line.new_line_number or '&nbsp;'
            content = line.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            html_lines.append(f'<tr class="{css_class}">')
            html_lines.append(f'<td class="line-num">{old_num}</td>')
            html_lines.append(f'<td class="line-num">{new_num}</td>')
            html_lines.append(f'<td class="line-content">{content}</td>')
            html_lines.append('</tr>')
        
        html_lines.append('</table>')
        html_lines.append('</div>')
        
        return '\n'.join(html_lines)

    @staticmethod
    def format_diff_text(diff_result: DiffResult) -> str:
        output = []
        output.append('--- Before')
        output.append('+++ After')
        
        for line in diff_result.lines:
            prefix = {
                ChangeType.ADDED: '+ ',
                ChangeType.REMOVED: '- ',
                ChangeType.UNCHANGED: '  '
            }.get(line.change_type, '  ')
            
            output.append(f"{prefix}{line.content}")
        
        return '\n'.join(output)

    @staticmethod
    def compare_command_results(results1: List[Dict[str, Any]], 
                               results2: List[Dict[str, Any]]) -> Dict[str, Any]:
        comparison = {}
        
        result_map1 = {r.get('hostname'): r for r in results1}
        result_map2 = {r.get('hostname'): r for r in results2}
        
        all_hosts = set(result_map1.keys()) | set(result_map2.keys())
        
        for hostname in all_hosts:
            r1 = result_map1.get(hostname, {})
            r2 = result_map2.get(hostname, {})
            
            stdout1 = r1.get('stdout', '')
            stdout2 = r2.get('stdout', '')
            
            if stdout1 != stdout2:
                diff = DiffTool.compare_text(stdout1, stdout2)
                comparison[hostname] = {
                    'has_changes': diff.has_changes,
                    'diff': diff,
                    'exit_code1': r1.get('exit_code'),
                    'exit_code2': r2.get('exit_code')
                }
        
        return comparison

    @staticmethod
    def compare_host_configs(hostname: str, old_config: str, 
                           new_config: str, config_path: str) -> Dict[str, Any]:
        diff = DiffTool.compare_text(old_config, new_config)
        
        return {
            'hostname': hostname,
            'config_path': config_path,
            'has_changes': diff.has_changes,
            'diff': diff,
            'stats': diff.stats
        }


class ResultComparator:
    def __init__(self):
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def take_snapshot(self, name: str, results: List[Dict[str, Any]]):
        self.snapshots[name] = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'results': results
        }

    def compare_snapshots(self, name1: str, name2: str) -> Optional[Dict[str, Any]]:
        if name1 not in self.snapshots or name2 not in self.snapshots:
            return None
        
        s1 = self.snapshots[name1]['results']
        s2 = self.snapshots[name2]['results']
        
        return DiffTool.compare_command_results(s1, s2)

    def list_snapshots(self) -> List[str]:
        return list(self.snapshots.keys())

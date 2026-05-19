import re
import logging
from typing import Dict, Optional, List


class NLPParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.action_patterns = {
            'restart': [
                r'(重启|restart|重启一下|重新启动)\s*(pod|容器)?\s*(在|位于|属于)?\s*命名空间\s*(?P<namespace>[\w-]+)?\s*(中|里)?\s*(的)?\s*(?P<pod>[\w-]+)?',
                r'(?P<pod>[\w-]+)\s*(pod|容器)?\s*(重启|restart)',
                r'重启\s*(?P<pod>[\w-]+)',
            ],
            'logs': [
                r'(查看|获取|看一下|展示)?\s*(日志|logs)\s*(在|位于|属于)?\s*命名空间\s*(?P<namespace>[\w-]+)?\s*(中|里)?\s*(的)?\s*(?P<pod>[\w-]+)?',
                r'(?P<pod>[\w-]+)\s*(的)?\s*(日志|logs)',
                r'日志\s*(?P<pod>[\w-]+)',
            ],
            'status': [
                r'(查看|获取|检查)?\s*(状态|status)\s*(在|位于|属于)?\s*命名空间\s*(?P<namespace>[\w-]+)?\s*(中|里)?\s*(的)?\s*(?P<pod>[\w-]+)?',
                r'(?P<pod>[\w-]+)\s*(的)?\s*(状态|status)',
                r'状态\s*(?P<pod>[\w-]+)',
            ],
            'list_pods': [
                r'(列出|展示|查看|获取)?\s*(所有)?\s*(pod|容器|pods)\s*(在|位于|属于)?\s*命名空间\s*(?P<namespace>[\w-]+)?',
                r'有什么\s*(pod|容器)',
            ],
            'describe': [
                r'(详细|describe)\s*(查看)?\s*(?P<pod>[\w-]+)',
                r'(?P<pod>[\w-]+)\s*(详细信息|详情)',
            ],
            'help': [
                r'(帮助|help|怎么用|使用说明)',
                r'(能做什么|有什么功能|支持什么)',
            ]
        }
        
        self.default_namespace = 'default'

    def parse(self, text: str) -> Dict:
        text = text.lower().strip()
        
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    result = {
                        'action': action,
                        'namespace': match.group('namespace') if 'namespace' in match.groupdict() else self.default_namespace,
                        'pod': match.group('pod') if 'pod' in match.groupdict() else None,
                        'raw_text': text
                    }
                    
                    if not result['namespace']:
                        result['namespace'] = self.default_namespace
                    
                    self.logger.info(f"Parsed command: {result}")
                    return result
        
        return {
            'action': 'unknown',
            'raw_text': text,
            'namespace': self.default_namespace
        }

    def format_response(self, action_result: Dict) -> str:
        action = action_result.get('action', 'unknown')
        
        if action == 'unknown':
            return "抱歉，我没有理解您的意思。请尝试说：\n• 重启 Pod名\n• 查看 Pod名 的日志\n• 检查 Pod名 的状态\n• 列出所有 Pod"
        
        if action == 'help':
            return self._get_help_message()
        
        success = action_result.get('success', False)
        message = action_result.get('message', '')
        data = action_result.get('data', {})
        
        if action == 'restart':
            if success:
                return f":white_check_mark: 成功重启 Pod: {action_result.get('pod', 'unknown')}\n{message}"
            else:
                return f":x: 重启失败: {message}"
        
        elif action == 'logs':
            if success:
                logs = data.get('logs', '')
                if len(logs) > 2000:
                    logs = logs[:2000] + "\n... (日志已截断)"
                return f":page_facing_up: Pod 日志:\n```\n{logs}\n```"
            else:
                return f":x: 获取日志失败: {message}"
        
        elif action == 'status':
            if success:
                status_text = f":information_source: Pod 状态:\n"
                status_text += f"• 阶段: {data.get('phase', 'Unknown')}\n"
                status_text += f"• Pod IP: {data.get('pod_ip', 'N/A')}\n"
                status_text += f"• 主机 IP: {data.get('host_ip', 'N/A')}\n"
                return status_text
            else:
                return f":x: 获取状态失败: {message}"
        
        elif action == 'list_pods':
            if success:
                pods = data.get('pods', [])
                if not pods:
                    return f":information_source: 命名空间 {action_result.get('namespace', 'default')} 中没有 Pod"
                pod_list = "\n".join([f"• {p}" for p in pods])
                return f":clipboard: Pod 列表:\n{pod_list}"
            else:
                return f":x: 获取列表失败: {message}"
        
        return message

    def _get_help_message(self) -> str:
        return """
:robot: Kubernetes 事件机器人使用说明

*支持的命令:*

• *重启 Pod*:
  `重启 my-pod`
  `重启命名空间 default 的 my-pod`

• *查看日志*:
  `查看 my-pod 的日志`
  `logs my-pod`

• *检查状态*:
  `检查 my-pod 的状态`
  `status my-pod`

• *列出 Pod*:
  `列出所有 Pod`
  `list pods in default`

• *获取帮助*:
  `help`
  `帮助`

*提示*: 支持中英文混合输入~
        """.strip()

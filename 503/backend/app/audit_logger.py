from datetime import datetime
from collections import deque
import json
import os


class AuditLogger:
    def __init__(self, log_file='optimization_audit.log', max_history=1000):
        self.log_file = log_file
        self.max_history = max_history
        self.audit_logs = deque(maxlen=max_history)
        self._load_from_file()

    def _load_from_file(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            self.audit_logs.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Error loading audit log: {e}")

    def _save_to_file(self, entry):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Error saving audit log: {e}")

    def log_optimization_action(self, action_type, target_key, description, status='pending', metadata=None):
        entry = {
            'id': len(self.audit_logs) + 1,
            'timestamp': datetime.now().timestamp(),
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action_type': action_type,
            'target_key': target_key,
            'description': description,
            'status': status,
            'metadata': metadata or {},
            'result': None
        }
        
        self.audit_logs.append(entry)
        self._save_to_file(entry)
        return entry

    def log_optimization_executed(self, entry_id, result, status='completed'):
        for entry in self.audit_logs:
            if entry['id'] == entry_id:
                entry['status'] = status
                entry['result'] = result
                entry['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._save_to_file(entry)
                return entry
        return None

    def log_key_optimization(self, key, key_type, optimization_type, commands, status='planned'):
        return self.log_optimization_action(
            action_type=f'{key_type}_{optimization_type}',
            target_key=key,
            description=f'{optimization_type} optimization for {key_type} key: {key}',
            status=status,
            metadata={
                'key': key,
                'key_type': key_type,
                'optimization_type': optimization_type,
                'commands': commands
            }
        )

    def log_command_optimization(self, command, optimization_type, original_command, optimized_command):
        return self.log_optimization_action(
            action_type=f'command_{optimization_type}',
            target_key=command,
            description=f'{optimization_type} optimization for command: {command}',
            status='recommended',
            metadata={
                'command': command,
                'original_command': original_command,
                'optimized_command': optimized_command
            }
        )

    def log_prediction_action(self, prediction_type, details):
        return self.log_optimization_action(
            action_type=f'prediction_{prediction_type}',
            target_key='prediction',
            description=f'Prediction: {prediction_type}',
            status='generated',
            metadata=details
        )

    def get_audit_logs(self, action_type=None, status=None, limit=100):
        logs = list(self.audit_logs)
        
        if action_type:
            logs = [l for l in logs if l.get('action_type') == action_type]
        
        if status:
            logs = [l for l in logs if l.get('status') == status]
        
        return sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_statistics(self):
        total = len(self.audit_logs)
        
        status_counts = {}
        type_counts = {}
        
        for log in self.audit_logs:
            status = log.get('status', 'unknown')
            action_type = log.get('action_type', 'unknown')
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
        
        pending = sum(1 for l in self.audit_logs if l.get('status') in ['pending', 'planned', 'recommended'])
        completed = sum(1 for l in self.audit_logs if l.get('status') == 'completed')
        failed = sum(1 for l in self.audit_logs if l.get('status') == 'failed')
        
        return {
            'total_entries': total,
            'status_distribution': status_counts,
            'type_distribution': type_counts,
            'pending_actions': pending,
            'completed_actions': completed,
            'failed_actions': failed,
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }

    def get_pending_optimizations(self):
        return [l for l in self.audit_logs if l.get('status') in ['pending', 'planned', 'recommended']]

    def clear_old_logs(self, days=30):
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        old_count = len(self.audit_logs)
        self.audit_logs = deque(
            [l for l in self.audit_logs if l.get('timestamp', 0) > cutoff],
            maxlen=self.max_history
        )
        return old_count - len(self.audit_logs)

    def mark_as_executed(self, entry_id, result=None):
        return self.log_optimization_executed(entry_id, result or 'Action executed successfully', 'completed')

    def mark_as_failed(self, entry_id, error_message=None):
        return self.log_optimization_executed(entry_id, error_message or 'Action failed', 'failed')

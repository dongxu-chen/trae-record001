import uuid
from celery import group
from typing import Dict, Any, List

from celery_config import app
from ..host_manager import HostManager, Host
from ..ssh_client import SSHClient
from ..ssh_pool import get_pooled_client
from ..file_distributor import FileDistributor
from ..audit import AuditLogger
from ..rollback import VersionedRollbackManager

host_manager = HostManager()
file_distributor = FileDistributor(use_connection_pool=True)
audit_logger = AuditLogger()
rollback_manager = VersionedRollbackManager()


@app.task(bind=True, name='execute_command')
def execute_command_task(self, host_data: Dict[str, Any], command: str, 
                        task_id: str, operator: str = 'system',
                        use_pool: bool = True) -> Dict[str, Any]:
    host = Host.from_dict(host_data)
    result = {
        'hostname': host.hostname,
        'command': command,
        'success': False
    }
    
    try:
        client_context = get_pooled_client(host) if use_pool else SSHClient(host)
        with client_context as client:
            cmd_result = client.execute_command(command)
            result.update(cmd_result)
        
        audit_logger.log_command_execution(
            task_id=task_id,
            hostname=host.hostname,
            command=command,
            result=result,
            operator=operator
        )
    except Exception as e:
        result['error'] = str(e)
        result['stderr'] = str(e)
    
    return result


@app.task(bind=True, name='distribute_file')
def distribute_file_task(self, host_data: Dict[str, Any], local_path: str,
                        remote_path: str, task_id: str, backup: bool = True,
                        versioned: bool = True, operator: str = 'system') -> Dict[str, Any]:
    host = Host.from_dict(host_data)
    result = file_distributor.distribute_file(
        host, local_path, remote_path, backup, versioned
    )
    
    audit_logger.log_file_distribution(
        task_id=task_id,
        hostname=host.hostname,
        remote_path=remote_path,
        backup_path=result.get('backup_path'),
        success=result.get('success', False),
        operator=operator,
        error=result.get('error')
    )
    
    return result


@app.task(bind=True, name='distribute_template')
def distribute_template_task(self, host_data: Dict[str, Any], template_name: str,
                            remote_path: str, context: Dict[str, Any],
                            task_id: str, backup: bool = True,
                            versioned: bool = True, auto_shell_escape: bool = False,
                            operator: str = 'system') -> Dict[str, Any]:
    host = Host.from_dict(host_data)
    host_context = dict(context)
    host_context['host'] = {
        'hostname': host.hostname,
        'ip': host.ip,
        'port': host.port,
        'username': host.username
    }
    
    result = file_distributor.distribute_template(
        host, template_name, remote_path, host_context, 
        backup, versioned, auto_shell_escape
    )
    
    audit_logger.log_template_render(
        task_id=task_id,
        hostname=host.hostname,
        template_name=template_name,
        remote_path=remote_path,
        success=result.get('success', False),
        operator=operator,
        error=result.get('error')
    )
    
    return result


def batch_execute_command(host_spec: str, command: str, 
                         operator: str = 'system',
                         use_pool: bool = True) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    hosts = host_manager.resolve_hosts(host_spec)
    
    if not hosts:
        return {
            'task_id': task_id,
            'success': False,
            'error': 'No hosts found'
        }
    
    audit_logger.log_task_start(
        task_id=task_id,
        task_type='batch_command',
        hostnames=[h.hostname for h in hosts],
        operator=operator
    )
    
    job = group(
        execute_command_task.s(
            host_data=h.to_dict(),
            command=command,
            task_id=task_id,
            operator=operator,
            use_pool=use_pool
        ) for h in hosts
    )
    
    result = job.apply_async()
    result.save()
    
    return {
        'task_id': task_id,
        'group_id': result.id,
        'task_type': 'batch_command',
        'total_hosts': len(hosts),
        'hosts': [h.hostname for h in hosts]
    }


def batch_distribute_file(host_spec: str, local_path: str, remote_path: str,
                         backup: bool = True, versioned: bool = True,
                         operator: str = 'system') -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    hosts = host_manager.resolve_hosts(host_spec)
    
    if not hosts:
        return {
            'task_id': task_id,
            'success': False,
            'error': 'No hosts found'
        }
    
    audit_logger.log_task_start(
        task_id=task_id,
        task_type='batch_file_distribution',
        hostnames=[h.hostname for h in hosts],
        operator=operator
    )
    
    job = group(
        distribute_file_task.s(
            host_data=h.to_dict(),
            local_path=local_path,
            remote_path=remote_path,
            task_id=task_id,
            backup=backup,
            versioned=versioned,
            operator=operator
        ) for h in hosts
    )
    
    result = job.apply_async()
    result.save()
    
    return {
        'task_id': task_id,
        'group_id': result.id,
        'task_type': 'batch_file_distribution',
        'total_hosts': len(hosts),
        'hosts': [h.hostname for h in hosts]
    }


def batch_distribute_template(host_spec: str, template_name: str, remote_path: str,
                             context: Dict[str, Any], backup: bool = True,
                             versioned: bool = True, auto_shell_escape: bool = False,
                             operator: str = 'system') -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    hosts = host_manager.resolve_hosts(host_spec)
    
    if not hosts:
        return {
            'task_id': task_id,
            'success': False,
            'error': 'No hosts found'
        }
    
    audit_logger.log_task_start(
        task_id=task_id,
        task_type='batch_template_distribution',
        hostnames=[h.hostname for h in hosts],
        operator=operator
    )
    
    job = group(
        distribute_template_task.s(
            host_data=h.to_dict(),
            template_name=template_name,
            remote_path=remote_path,
            context=context,
            task_id=task_id,
            backup=backup,
            versioned=versioned,
            auto_shell_escape=auto_shell_escape,
            operator=operator
        ) for h in hosts
    )
    
    result = job.apply_async()
    result.save()
    
    return {
        'task_id': task_id,
        'group_id': result.id,
        'task_type': 'batch_template_distribution',
        'total_hosts': len(hosts),
        'hosts': [h.hostname for h in hosts]
    }


def get_task_result(group_id: str) -> Dict[str, Any]:
    from celery.result import GroupResult
    result = GroupResult.restore(group_id)
    if not result:
        return {'error': 'Task not found'}
    
    results = []
    for r in result.results:
        if r.ready():
            if r.successful():
                results.append(r.result)
            else:
                results.append({'error': str(r.result)})
        else:
            results.append({'status': 'pending'})
    
    return {
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'completed': sum(1 for r in result.results if r.ready()),
        'total': len(result.results),
        'results': results
    }


@app.task(name='execute_rollback_task')
def execute_rollback_task(task_id: str, operator: str = 'system',
                         use_pool: bool = True) -> Dict[str, Any]:
    return rollback_manager.rollback_task(task_id, operator, use_pool)


@app.task(name='create_version_task')
def create_version_task(hostname: str, remote_path: str, 
                       description: str = '', operator: str = 'system',
                       use_pool: bool = True) -> Dict[str, Any]:
    return rollback_manager.create_version(
        hostname, remote_path, description, operator, use_pool
    )


@app.task(name='restore_version_task')
def restore_version_task(hostname: str, remote_path: str, version_id: str,
                        operator: str = 'system', use_pool: bool = True) -> Dict[str, Any]:
    return rollback_manager.restore_version(
        hostname, remote_path, version_id, operator, use_pool
    )

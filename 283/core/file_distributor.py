import os
from typing import Dict, Any, List, Optional
from .ssh_client import SSHClient
from .ssh_pool import get_pooled_client
from .template_renderer import TemplateRenderer
from .host_manager import Host


class FileDistributor:
    def __init__(self, use_connection_pool: bool = True):
        self.template_renderer = TemplateRenderer()
        self.use_connection_pool = use_connection_pool

    def _get_client_context(self, host: Host):
        if self.use_connection_pool:
            return get_pooled_client(host)
        return SSHClient(host)

    def distribute_file(self, host: Host, local_path: str, 
                       remote_path: str, backup: bool = True,
                       versioned: bool = True) -> Dict[str, Any]:
        result = {
            'hostname': host.hostname,
            'local_path': local_path,
            'remote_path': remote_path,
            'success': False,
            'backup_path': None,
            'version_id': None
        }

        try:
            with self._get_client_context(host) as client:
                if backup and client.file_exists(remote_path):
                    if versioned:
                        import time
                        version_id = str(int(time.time()))
                        backup_result = client.backup_file(remote_path, version_id)
                    else:
                        backup_result = client.backup_file(remote_path)
                    
                    if backup_result['success']:
                        result['backup_path'] = backup_result['backup_path']
                        result['version_id'] = backup_result.get('version_id')
                
                upload_result = client.upload_file(local_path, remote_path)
                result['success'] = upload_result['success']
                if not upload_result['success']:
                    result['error'] = upload_result.get('error', 'Upload failed')
        except Exception as e:
            result['error'] = str(e)

        return result

    def distribute_template(self, host: Host, template_name: str, 
                           remote_path: str, context: Dict[str, Any],
                           backup: bool = True, versioned: bool = True,
                           auto_shell_escape: bool = False) -> Dict[str, Any]:
        result = {
            'hostname': host.hostname,
            'template_name': template_name,
            'remote_path': remote_path,
            'success': False,
            'backup_path': None,
            'version_id': None,
            'rendered_content': None
        }

        try:
            rendered_content = self.template_renderer.render_template(
                template_name, context, auto_shell_escape
            )
            result['rendered_content'] = rendered_content

            with self._get_client_context(host) as client:
                if backup and client.file_exists(remote_path):
                    if versioned:
                        import time
                        version_id = str(int(time.time()))
                        backup_result = client.backup_file(remote_path, version_id)
                    else:
                        backup_result = client.backup_file(remote_path)
                    
                    if backup_result['success']:
                        result['backup_path'] = backup_result['backup_path']
                        result['version_id'] = backup_result.get('version_id')
                
                upload_result = client.upload_content(rendered_content, remote_path)
                result['success'] = upload_result['success']
                if not upload_result['success']:
                    result['error'] = upload_result.get('error', 'Upload failed')
        except Exception as e:
            result['error'] = str(e)

        return result

    def distribute_content(self, host: Host, content: str, 
                          remote_path: str, backup: bool = True,
                          versioned: bool = True) -> Dict[str, Any]:
        result = {
            'hostname': host.hostname,
            'remote_path': remote_path,
            'success': False,
            'backup_path': None,
            'version_id': None
        }

        try:
            with self._get_client_context(host) as client:
                if backup and client.file_exists(remote_path):
                    if versioned:
                        import time
                        version_id = str(int(time.time()))
                        backup_result = client.backup_file(remote_path, version_id)
                    else:
                        backup_result = client.backup_file(remote_path)
                    
                    if backup_result['success']:
                        result['backup_path'] = backup_result['backup_path']
                        result['version_id'] = backup_result.get('version_id')
                
                upload_result = client.upload_content(content, remote_path)
                result['success'] = upload_result['success']
                if not upload_result['success']:
                    result['error'] = upload_result.get('error', 'Upload failed')
        except Exception as e:
            result['error'] = str(e)

        return result

    def batch_distribute_file(self, hosts: List[Host], local_path: str,
                             remote_path: str, backup: bool = True,
                             versioned: bool = True) -> List[Dict[str, Any]]:
        results = []
        for host in hosts:
            result = self.distribute_file(host, local_path, remote_path, backup, versioned)
            results.append(result)
        return results

    def batch_distribute_template(self, hosts: List[Host], template_name: str,
                                 remote_path: str, context: Dict[str, Any],
                                 backup: bool = True, versioned: bool = True,
                                 auto_shell_escape: bool = False) -> List[Dict[str, Any]]:
        results = []
        for host in hosts:
            host_context = dict(context)
            host_context['host'] = {
                'hostname': host.hostname,
                'ip': host.ip,
                'port': host.port,
                'username': host.username
            }
            result = self.distribute_template(
                host, template_name, remote_path, host_context, 
                backup, versioned, auto_shell_escape
            )
            results.append(result)
        return results

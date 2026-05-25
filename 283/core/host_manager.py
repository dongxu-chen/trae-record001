import json
import os
from typing import Dict, List, Optional
from config import HOSTS_FILE


class Host:
    def __init__(self, hostname: str, ip: str, port: int = 22,
                 username: str = 'root', password: Optional[str] = None,
                 private_key: Optional[str] = None, groups: Optional[List[str]] = None):
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.groups = groups or []

    def to_dict(self) -> Dict:
        return {
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'private_key': self.private_key,
            'groups': self.groups
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Host':
        return cls(
            hostname=data['hostname'],
            ip=data['ip'],
            port=data.get('port', 22),
            username=data.get('username', 'root'),
            password=data.get('password'),
            private_key=data.get('private_key'),
            groups=data.get('groups', [])
        )


class HostManager:
    def __init__(self):
        self.hosts: Dict[str, Host] = {}
        self._load_hosts()

    def _load_hosts(self):
        if os.path.exists(HOSTS_FILE):
            with open(HOSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for host_data in data:
                    host = Host.from_dict(host_data)
                    self.hosts[host.hostname] = host

    def _save_hosts(self):
        data = [host.to_dict() for host in self.hosts.values()]
        with open(HOSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_host(self, host: Host) -> bool:
        if host.hostname in self.hosts:
            return False
        self.hosts[host.hostname] = host
        self._save_hosts()
        return True

    def remove_host(self, hostname: str) -> bool:
        if hostname not in self.hosts:
            return False
        del self.hosts[hostname]
        self._save_hosts()
        return True

    def get_host(self, hostname: str) -> Optional[Host]:
        return self.hosts.get(hostname)

    def list_hosts(self) -> List[Host]:
        return list(self.hosts.values())

    def get_hosts_by_group(self, group: str) -> List[Host]:
        return [host for host in self.hosts.values() if group in host.groups]

    def get_all_groups(self) -> List[str]:
        groups = set()
        for host in self.hosts.values():
            groups.update(host.groups)
        return sorted(list(groups))

    def update_host(self, hostname: str, **kwargs) -> bool:
        if hostname not in self.hosts:
            return False
        host = self.hosts[hostname]
        for key, value in kwargs.items():
            if hasattr(host, key):
                setattr(host, key, value)
        self._save_hosts()
        return True

    def resolve_hosts(self, host_spec: str) -> List[Host]:
        hosts = []
        specs = [s.strip() for s in host_spec.split(',')]
        
        for spec in specs:
            if spec.startswith('@'):
                group = spec[1:]
                hosts.extend(self.get_hosts_by_group(group))
            elif spec in self.hosts:
                hosts.append(self.hosts[spec])
        
        seen = set()
        unique_hosts = []
        for host in hosts:
            if host.hostname not in seen:
                seen.add(host.hostname)
                unique_hosts.append(host)
        return unique_hosts

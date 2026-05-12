[web_servers]
${instance_id} ansible_host=${public_ip} ansible_user=${user} ansible_ssh_private_key_file=${key_path} ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[web_servers:vars]
ansible_python_interpreter=/usr/bin/python3

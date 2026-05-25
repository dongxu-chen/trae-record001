import click
import json
import time
from tabulate import tabulate

from core.host_manager import HostManager, Host
from core.template_renderer import TemplateRenderer
from core.audit import AuditLogger
from core.rollback import VersionedRollbackManager
from core.ssh_pool import SSHConnectionPool
from core.diff_tool import DiffTool
from core.tasks.execution_tasks import (
    batch_execute_command,
    batch_distribute_file,
    batch_distribute_template,
    get_task_result
)

host_manager = HostManager()
template_renderer = TemplateRenderer()
audit_logger = AuditLogger()
rollback_manager = VersionedRollbackManager()
connection_pool = SSHConnectionPool()


@click.group()
def cli():
    pass


@cli.group()
def host():
    pass


@host.command('add')
@click.option('--hostname', required=True, help='主机名')
@click.option('--ip', required=True, help='IP地址')
@click.option('--port', default=22, help='SSH端口')
@click.option('--username', default='root', help='用户名')
@click.option('--password', help='密码')
@click.option('--private-key', help='私钥文件路径')
@click.option('--groups', help='分组，逗号分隔')
def add_host(hostname, ip, port, username, password, private_key, groups):
    if private_key:
        with open(private_key, 'r') as f:
            private_key_content = f.read()
    else:
        private_key_content = None
    
    group_list = [g.strip() for g in groups.split(',')] if groups else []
    
    host = Host(
        hostname=hostname,
        ip=ip,
        port=port,
        username=username,
        password=password,
        private_key=private_key_content,
        groups=group_list
    )
    
    if host_manager.add_host(host):
        click.echo(f'主机 {hostname} 添加成功')
    else:
        click.echo(f'主机 {hostname} 已存在')


@host.command('list')
def list_hosts():
    hosts = host_manager.list_hosts()
    if not hosts:
        click.echo('没有主机')
        return
    
    table = []
    for h in hosts:
        table.append([
            h.hostname,
            h.ip,
            h.port,
            h.username,
            ','.join(h.groups)
        ])
    
    click.echo(tabulate(table, headers=['主机名', 'IP', '端口', '用户名', '分组']))


@host.command('groups')
def list_groups():
    groups = host_manager.get_all_groups()
    for g in groups:
        hosts = host_manager.get_hosts_by_group(g)
        click.echo(f'{g}: {", ".join(h.hostname for h in hosts)}')


@host.command('remove')
@click.argument('hostname')
def remove_host(hostname):
    if host_manager.remove_host(hostname):
        click.echo(f'主机 {hostname} 已删除')
    else:
        click.echo(f'主机 {hostname} 不存在')


@cli.group()
def exec():
    pass


@exec.command('command')
@click.argument('host_spec')
@click.argument('command')
@click.option('--operator', default='cli', help='操作者')
@click.option('--wait/--no-wait', default=True, help='是否等待执行完成')
@click.option('--use-pool/--no-pool', default=True, help='是否使用连接池')
def exec_command(host_spec, command, operator, wait, use_pool):
    result = batch_execute_command(host_spec, command, operator, use_pool)
    click.echo(f"任务ID: {result['task_id']}")
    click.echo(f"Group ID: {result['group_id']}")
    click.echo(f"目标主机: {', '.join(result['hosts'])}")
    
    if wait:
        while True:
            task_result = get_task_result(result['group_id'])
            if task_result.get('ready'):
                break
            click.echo(f"进度: {task_result.get('completed', 0)}/{task_result.get('total', 0)}")
            time.sleep(2)
        
        click.echo('\n执行结果:')
        for r in task_result['results']:
            status = '成功' if r.get('success') else '失败'
            click.echo(f"\n{r.get('hostname')} - {status}")
            if r.get('stdout'):
                click.echo(f"STDOUT:\n{r.get('stdout')}")
            if r.get('stderr'):
                click.echo(f"STDERR:\n{r.get('stderr')}")


@cli.group()
def file():
    pass


@file.command('distribute')
@click.argument('host_spec')
@click.argument('local_path')
@click.argument('remote_path')
@click.option('--backup/--no-backup', default=True, help='是否备份')
@click.option('--versioned/--no-versioned', default=True, help='是否使用版本化备份')
@click.option('--operator', default='cli', help='操作者')
def distribute_file(host_spec, local_path, remote_path, backup, versioned, operator):
    result = batch_distribute_file(
        host_spec, local_path, remote_path, backup, versioned, operator
    )
    click.echo(f"任务ID: {result['task_id']}")
    click.echo(f"Group ID: {result['group_id']}")
    click.echo(f"目标主机: {', '.join(result['hosts'])}")


@cli.group()
def template():
    pass


@template.command('list')
def list_templates():
    templates = template_renderer.list_templates()
    for t in templates:
        click.echo(t)


@template.command('render')
@click.argument('template_name')
@click.option('--context', help='JSON格式的上下文')
@click.option('--output', help='输出文件路径')
@click.option('--auto-escape/--no-auto-escape', default=False, help='是否自动shell转义')
def render_template(template_name, context, output, auto_escape):
    ctx = json.loads(context) if context else {}
    content = template_renderer.render_template(template_name, ctx, auto_escape)
    
    if output:
        with open(output, 'w') as f:
            f.write(content)
        click.echo(f'已渲染到 {output}')
    else:
        click.echo(content)


@template.command('distribute')
@click.argument('host_spec')
@click.argument('template_name')
@click.argument('remote_path')
@click.option('--context', help='JSON格式的上下文')
@click.option('--backup/--no-backup', default=True, help='是否备份')
@click.option('--versioned/--no-versioned', default=True, help='是否使用版本化备份')
@click.option('--auto-escape/--no-auto-escape', default=False, help='是否自动shell转义')
@click.option('--operator', default='cli', help='操作者')
def distribute_template(host_spec, template_name, remote_path, context, backup, versioned, auto_escape, operator):
    ctx = json.loads(context) if context else {}
    result = batch_distribute_template(
        host_spec, template_name, remote_path, ctx, 
        backup, versioned, auto_escape, operator
    )
    click.echo(f"任务ID: {result['task_id']}")
    click.echo(f"Group ID: {result['group_id']}")
    click.echo(f"目标主机: {', '.join(result['hosts'])}")


@cli.group()
def task():
    pass


@task.command('status')
@click.argument('group_id')
def task_status(group_id):
    result = get_task_result(group_id)
    click.echo(f"完成: {result.get('completed')}/{result.get('total')}")
    click.echo(f"就绪: {result.get('ready')}")
    
    if result.get('ready'):
        click.echo('\n结果:')
        for r in result['results']:
            status = '成功' if r.get('success') else '失败'
            click.echo(f"  {r.get('hostname')}: {status}")


@cli.group()
def audit():
    pass


@audit.command('logs')
@click.option('--task-id', help='任务ID')
@click.option('--type', 'log_type', help='日志类型')
@click.option('--limit', default=50, help='显示条数')
def audit_logs(task_id, log_type, limit):
    logs = audit_logger.get_logs(task_id=task_id, log_type=log_type, limit=limit)
    for log in logs:
        click.echo(f"{log['timestamp']} - {log['type']} - {log.get('hostname', '')}")
        if log['type'] == 'command_execution':
            click.echo(f"  命令: {log.get('command')}")
            click.echo(f"  成功: {log.get('success')}")


@cli.group()
def version():
    pass


@version.command('create')
@click.argument('hostname')
@click.argument('remote_path')
@click.option('--description', default='', help='版本描述')
@click.option('--operator', default='cli', help='操作者')
def create_version(hostname, remote_path, description, operator):
    result = rollback_manager.create_version(
        hostname, remote_path, description, operator, use_pool=True
    )
    if result.get('success'):
        click.echo(f"版本创建成功")
        click.echo(f"  版本ID: {result['version_id']}")
        click.echo(f"  备份路径: {result['backup_path']}")
        if result.get('file_info'):
            click.echo(f"  文件大小: {result['file_info'].get('size', 0)} bytes")
    else:
        click.echo(f"版本创建失败: {result.get('error', 'Unknown error')}")


@version.command('list')
@click.argument('hostname')
@click.argument('remote_path')
@click.option('--limit', default=20, help='显示条数')
def list_versions(hostname, remote_path, limit):
    versions = rollback_manager.get_file_versions(hostname, remote_path, limit)
    if not versions:
        click.echo('没有找到版本记录')
        return
    
    table = []
    for v in versions:
        table.append([
            v['version_id'],
            v.get('description', '')[:30],
            v['operator'],
            v['created_at'][:19],
            v.get('file_size', 0),
            '自动' if v.get('auto_created') else '手动'
        ])
    
    click.echo(tabulate(table, headers=['版本ID', '描述', '操作者', '创建时间', '大小', '类型']))


@version.command('list-all')
@click.option('--hostname', help='过滤主机名')
def list_all_versions(hostname):
    versions = rollback_manager.list_all_versions(hostname)
    if not versions:
        click.echo('没有找到版本记录')
        return
    
    table = []
    for v in versions:
        table.append([
            v['version_id'],
            v['hostname'],
            v['remote_path'][-40:],
            v.get('description', '')[:20],
            v['created_at'][:19]
        ])
    
    click.echo(tabulate(table, headers=['版本ID', '主机', '路径', '描述', '创建时间']))


@version.command('restore')
@click.argument('hostname')
@click.argument('remote_path')
@click.argument('version_id')
@click.option('--operator', default='cli', help='操作者')
def restore_version(hostname, remote_path, version_id, operator):
    result = rollback_manager.restore_version(
        hostname, remote_path, version_id, operator, use_pool=True
    )
    if result.get('success'):
        click.echo(f"版本恢复成功")
        click.echo(f"  恢复到版本: {version_id}")
        if result.get('auto_backup'):
            click.echo(f"  当前版本已备份: {result['auto_backup']}")
    else:
        click.echo(f"版本恢复失败: {result.get('error', 'Unknown error')}")


@version.command('diff')
@click.argument('hostname')
@click.argument('remote_path')
@click.argument('version_id1')
@click.argument('version_id2')
def compare_versions(hostname, remote_path, version_id1, version_id2):
    result = rollback_manager.compare_versions(
        hostname, remote_path, version_id1, version_id2, use_pool=True
    )
    if result.get('success'):
        if result.get('has_changes'):
            click.echo(f"版本差异:\n{result['diff']}")
        else:
            click.echo('两个版本没有差异')
    else:
        click.echo(f"对比失败: {result.get('error', 'Unknown error')}")


@version.command('delete')
@click.argument('hostname')
@click.argument('remote_path')
@click.argument('version_id')
def delete_version(hostname, remote_path, version_id):
    result = rollback_manager.delete_version(
        hostname, remote_path, version_id, use_pool=True
    )
    if result.get('success'):
        click.echo(f"版本 {version_id} 已删除")
    else:
        click.echo(f"删除失败: {result.get('error', 'Unknown error')}")


@cli.group()
def rollback():
    pass


@rollback.command('list')
def list_rollbacks():
    tasks = rollback_manager.list_tasks()
    if not tasks:
        click.echo('没有可回滚的任务')
        return
    
    table = []
    for t in tasks:
        table.append([
            t['task_id'],
            t['task_type'],
            t['operator'],
            t['created_at'][:19],
            len(t.get('versions', []))
        ])
    
    click.echo(tabulate(table, headers=['任务ID', '类型', '操作者', '创建时间', '版本数']))


@rollback.command('execute')
@click.argument('task_id')
@click.option('--operator', default='cli', help='操作者')
def execute_rollback(task_id, operator):
    result = rollback_manager.rollback_task(task_id, operator, use_pool=True)
    if result.get('success'):
        click.echo('回滚成功')
    else:
        click.echo(f"回滚完成，成功: {result.get('success_count', 0)}/{result.get('total_count', 0)}")
    
    for r in result.get('results', []):
        status = '成功' if r.get('success') else '失败'
        click.echo(f"  {r.get('hostname')}: {status}")


@cli.group()
def pool():
    pass


@pool.command('stats')
def pool_stats():
    stats = connection_pool.get_stats()
    if not stats:
        click.echo('连接池为空')
        return
    
    table = []
    for key, s in stats.items():
        table.append([
            key,
            s['idle'],
            s['active']
        ])
    
    click.echo(tabulate(table, headers=['连接标识', '空闲', '使用中']))


@pool.command('close')
def close_pool():
    connection_pool.close_all()
    click.echo('所有连接已关闭')


@cli.group()
def diff():
    pass


@diff.command('text')
@click.option('--old', 'old_file', help='旧文件路径')
@click.option('--new', 'new_file', help='新文件路径')
@click.option('--old-content', help='旧内容文本')
@click.option('--new-content', help='新内容文本')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json']), default='text', help='输出格式')
def diff_text(old_file, new_file, old_content, new_content, output_format):
    if old_file:
        with open(old_file, 'r', encoding='utf-8') as f:
            old_text = f.read()
    else:
        old_text = old_content or ''
    
    if new_file:
        with open(new_file, 'r', encoding='utf-8') as f:
            new_text = f.read()
    else:
        new_text = new_content or ''
    
    result = DiffTool.compare_text(old_text, new_text)
    
    if output_format == 'json':
        output = {
            'has_changes': result.has_changes,
            'stats': result.stats,
            'diff': DiffTool.format_diff_text(result)
        }
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if result.has_changes:
            click.echo(DiffTool.format_diff_text(result))
            click.echo(f"\n统计: 新增 {result.stats['added']} 行, 删除 {result.stats['removed']} 行")
        else:
            click.echo('没有差异')


@cli.group()
def web():
    pass


@web.command('start')
@click.option('--host', default='0.0.0.0', help='监听地址')
@click.option('--port', default=5000, type=int, help='监听端口')
@click.option('--debug/--no-debug', default=False, help='调试模式')
def start_web(host, port, debug):
    from web.app import run_server
    click.echo(f'启动Web服务: http://{host}:{port}')
    click.echo('Web Terminal: http://{host}:{port}/terminal'.format(host=host, port=port))
    run_server(host=host, port=port, debug=debug)


if __name__ == '__main__':
    cli()

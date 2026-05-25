#!/usr/bin/env python3
import click
import sys
from pathlib import Path
from k8s_linter import (
    K8sConfigDetector,
    ReportFormatter,
    YamllintIntegration,
    KubeScoreIntegration,
    AutoFixer,
    ClusterConfigComparer,
    AdmissionController,
    WebhookServer,
    Severity
)

@click.group()
def cli():
    """Kubernetes 配置错误检测工具"""
    pass

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--rules', '-r', type=click.Path(exists=True), help='自定义规则配置文件')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['console', 'json', 'junit']),
              default='console', help='输出格式')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--yamllint/--no-yamllint', default=True, help='启用/禁用yamllint集成')
@click.option('--kube-score/--no-kube-score', default=True, help='启用/禁用kube-score集成')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息和修复建议')
@click.option('--strict', '-s', is_flag=True, help='严格模式，发现任何错误都返回非零退出码')
def scan(path, rules, output_format, output, yamllint, kube_score, verbose, strict):
    """扫描Kubernetes配置文件"""
    click.echo(f"正在扫描: {path}")
    click.echo("")

    detector = K8sConfigDetector(rules_config_path=rules)

    path_obj = Path(path)
    if path_obj.is_file():
        report = detector.scan_file(path)
        if yamllint:
            yamllint_int = YamllintIntegration()
            report = yamllint_int.run(path, report)
        if kube_score:
            kube_score_int = KubeScoreIntegration()
            report = kube_score_int.run(path, report)
    else:
        report = detector.scan_directory(path)
        if yamllint or kube_score:
            for yaml_file in list(path_obj.rglob("*.yaml")) + list(path_obj.rglob("*.yml")):
                if yaml_file.is_file():
                    if yamllint:
                        yamllint_int = YamllintIntegration()
                        report = yamllint_int.run(str(yaml_file), report)
                    if kube_score:
                        kube_score_int = KubeScoreIntegration()
                        report = kube_score_int.run(str(yaml_file), report)

    if output_format == 'console':
        formatted = ReportFormatter.format_console(report, verbose=verbose)
    elif output_format == 'json':
        formatted = ReportFormatter.format_json(report)
    elif output_format == 'junit':
        formatted = ReportFormatter.format_junit(report)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(formatted)
        click.echo(f"结果已保存到: {output}")
    else:
        click.echo(formatted)

    if strict and report.has_errors:
        sys.exit(1)

@cli.command()
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
def init_rules(output):
    """生成默认规则配置文件"""
    import shutil
    default_rules = Path(__file__).parent / "config" / "rules.yaml"

    if output:
        shutil.copy(default_rules, output)
        click.echo(f"默认规则已导出到: {output}")
    else:
        with open(default_rules, 'r', encoding='utf-8') as f:
            click.echo(f.read())

@cli.command()
def list_rules():
    """列出所有可用的检测规则"""
    detector = K8sConfigDetector()
    rules = detector.rules

    click.echo("可用的检测规则:")
    click.echo("=" * 80)

    for category, category_rules in rules.items():
        click.echo(f"\n[{category.upper()}]")
        for rule_id, rule_config in category_rules.items():
            status = "✓" if rule_config.get('enabled', True) else "✗"
            severity = rule_config.get('severity', 'info')
            click.echo(f"  {status} {rule_id} ({severity})")
            click.echo(f"      {rule_config.get('message', '')}")


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出修复后的文件路径')
@click.option('--in-place', '-i', is_flag=True, help='直接修改源文件')
@click.option('--preview', '-p', is_flag=True, help='仅预览修复内容，不写入文件')
@click.option('--rules', '-r', type=click.Path(exists=True), help='自定义规则配置文件')
def fix(path, output, in_place, preview, rules):
    """自动修复配置文件"""
    click.echo(f"正在分析并准备修复: {path}")
    click.echo("")

    detector = K8sConfigDetector(rules_config_path=rules)
    auto_fixer = AutoFixer()

    path_obj = Path(path)
    if path_obj.is_file():
        report = detector.scan_file(path)
        fixes = auto_fixer.generate_fixes(report.issues)
        
        click.echo(f"发现 {len(report.issues)} 个问题，可修复 {len(fixes)} 个")
        
        if preview:
            click.echo("\n修复建议:")
            for i, fix in enumerate(fixes, 1):
                click.echo(f"  {i}. {fix.description} ({fix.rule_id})")
            
            click.echo("\n修复后的YAML预览:")
            _, result = auto_fixer.apply_fixes_to_file(path, issues=report.issues)
            click.echo(result)
        else:
            output_file = path if in_place else (output or f"{path_obj.stem}_fixed{path_obj.suffix}")
            success, result = auto_fixer.apply_fixes_to_file(path, output_file, report.issues)
            if success:
                click.echo(f"\n修复完成! 输出文件: {result}")
                summary = auto_fixer.get_fix_summary(fixes)
                click.echo(f"应用了 {summary['applied']}/{summary['total']} 个修复")
    else:
        click.echo("目录批量修复功能请使用 --recursive 选项")


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['console', 'json', 'summary']),
              default='console', help='输出格式')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
def drift(path, output_format, output):
    """检测运行中集群与YAML配置的漂移"""
    comparer = ClusterConfigComparer()
    
    if not comparer.is_available():
        click.echo("警告: 未找到 kubectl 命令，无法连接集群")
        click.echo("请确保已安装 kubectl 并配置好集群访问")
        return

    click.echo(f"正在检测配置漂移: {path}")
    click.echo("")

    path_obj = Path(path)
    if path_obj.is_file():
        reports = comparer.compare_file_with_cluster(path)
    else:
        reports = comparer.compare_directory_with_cluster(path)

    formatted = comparer.generate_diff_report(reports, output_format)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(formatted)
        click.echo(f"结果已保存到: {output}")
    else:
        click.echo(formatted)


@cli.group()
def webhook():
    """准入控制Webhook管理"""
    pass


@webhook.command()
@click.option('--host', '-H', default='0.0.0.0', help='监听地址')
@click.option('--port', '-p', default=8443, type=int, help='监听端口')
@click.option('--cert', '-c', type=click.Path(exists=True), help='TLS证书文件')
@click.option('--key', '-k', type=click.Path(exists=True), help='TLS私钥文件')
@click.option('--rules', '-r', type=click.Path(exists=True), help='自定义规则配置文件')
@click.option('--deny-severity', type=click.Choice(['critical', 'error', 'warning', 'info']),
              default='error', help='拒绝请求的错误等级')
def start(host, port, cert, key, rules, deny_severity):
    """启动准入控制Webhook服务器"""
    deny_severity_map = {
        'critical': Severity.CRITICAL,
        'error': Severity.ERROR,
        'warning': Severity.WARNING,
        'info': Severity.INFO
    }
    
    controller = AdmissionController(
        rules_config_path=rules,
        deny_on_severity=deny_severity_map[deny_severity]
    )
    
    server = WebhookServer(
        controller=controller,
        host=host,
        port=port,
        cert_file=cert,
        key_file=key
    )
    
    click.echo(f"启动准入控制Webhook服务器...")
    server.run()


@webhook.command()
@click.option('--name', '-n', default='k8s-lint-webhook', help='Webhook配置名称')
@click.option('--service', '-s', default='k8s-lint-webhook', help='Kubernetes服务名称')
@click.option('--namespace', '-ns', default='default', help='命名空间')
@click.option('--hostname', '-h', default='k8s-lint-webhook.default.svc', help='服务主机名')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--failure-policy', type=click.Choice(['Fail', 'Ignore']),
              default='Fail', help='失败策略')
def manifest(name, service, namespace, hostname, output, failure_policy):
    """生成Webhook部署清单"""
    try:
        from k8s_linter.admission_webhook import generate_webhook_manifest, generate_self_signed_cert
        
        click.echo(f"正在生成自签名证书...")
        cert_pem, key_pem, ca_bundle = generate_self_signed_cert(hostname)
        
        manifest = generate_webhook_manifest(name, service, namespace, ca_bundle, failure_policy)
        
        import yaml
        content = yaml.safe_dump(manifest, default_flow_style=False, sort_keys=False)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            click.echo(f"Webhook清单已保存到: {output}")
            
            cert_file = f"{Path(output).parent}/tls.crt"
            key_file = f"{Path(output).parent}/tls.key"
            with open(cert_file, 'wb') as f:
                f.write(cert_pem)
            with open(key_file, 'wb') as f:
                f.write(key_pem)
            click.echo(f"证书已保存到: {cert_file}")
            click.echo(f"私钥已保存到: {key_file}")
        else:
            click.echo(content)
    except ImportError as e:
        click.echo(f"需要安装 cryptography 包: pip install cryptography")
        return


if __name__ == '__main__':
    cli()

#!/usr/bin/env python3
import click
import json
from dbbackup.config import Config
from dbbackup.utils import setup_logging, format_size
from dbbackup.backup import BackupEngine
from dbbackup.verify import BackupVerifier
from dbbackup.recovery import PointInTimeRecovery
from dbbackup.storage import StorageFactory


@click.group()
@click.option('--config', '-c', default='config.yaml', help='Path to config file')
@click.option('--db-type', '-d', type=click.Choice(['mysql', 'postgresql']), required=True, help='Database type')
@click.pass_context
def cli(ctx, config, db_type):
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['db_type'] = db_type
    
    cfg = Config(config)
    setup_logging(cfg)
    ctx.obj['config'] = cfg


@cli.command()
@click.option('--strategy', '-s', type=click.Choice(['full', 'incremental']), default='full', help='Backup strategy')
@click.option('--verify/--no-verify', default=True, help='Verify backup after creation')
@click.pass_context
def backup(ctx, strategy, verify):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    engine = BackupEngine(config, db_type)
    verifier = BackupVerifier(config, db_type)
    
    try:
        click.echo(f"Creating {strategy} backup for {db_type}...")
        backup_info = engine.create_backup(strategy=strategy)
        
        click.echo(click.style("✓ Backup created successfully!", fg='green'))
        click.echo(f"  Backup ID: {backup_info['backup_id']}")
        click.echo(f"  Raw size: {format_size(backup_info['raw_size'])}")
        click.echo(f"  Compressed size: {format_size(backup_info['compressed_size'])}")
        click.echo(f"  Final size: {format_size(backup_info['final_size'])}")
        click.echo(f"  MD5: {backup_info['md5']}")
        click.echo(f"  Remote path: {backup_info['remote_path']}")
        
        if verify:
            click.echo("\nVerifying backup...")
            success, result = verifier.verify_backup(backup_info)
            if success:
                click.echo(click.style("✓ Backup verification passed!", fg='green'))
            else:
                click.echo(click.style("✗ Backup verification failed!", fg='red'))
                click.echo(f"  Error: {result}")
                
    except Exception as e:
        click.echo(click.style(f"✗ Backup failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('list')
@click.option('--strategy', '-s', type=click.Choice(['full', 'incremental']), help='Filter by strategy')
@click.pass_context
def list_backups(ctx, strategy):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    engine = BackupEngine(config, db_type)
    
    try:
        backups = engine.list_backups(strategy=strategy)
        
        if not backups:
            click.echo("No backups found.")
            return
        
        click.echo(f"Found {len(backups)} backup(s):\n")
        
        for i, backup in enumerate(backups, 1):
            status_color = 'green' if backup['status'] == 'completed' else 'red'
            click.echo(f"{i}. {click.style(backup['backup_id'], fg='blue')}")
            click.echo(f"   Status: {click.style(backup['status'], fg=status_color)}")
            click.echo(f"   Strategy: {backup['strategy']}")
            click.echo(f"   Timestamp: {backup['timestamp']}")
            click.echo(f"   Size: {format_size(backup.get('final_size', 0))}")
            click.echo()
            
    except Exception as e:
        click.echo(click.style(f"✗ Failed to list backups: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command()
@click.argument('backup_id')
@click.option('--target-host', help='Target database host')
@click.option('--target-port', type=int, help='Target database port')
@click.option('--target-user', help='Target database user')
@click.option('--target-password', help='Target database password')
@click.option('--target-database', help='Target database name')
@click.pass_context
def restore(ctx, backup_id, target_host, target_port, target_user, target_password, target_database):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    target_config = {}
    if target_host:
        target_config['host'] = target_host
    if target_port:
        target_config['port'] = target_port
    if target_user:
        target_config['user'] = target_user
    if target_password:
        target_config['password'] = target_password
    if target_database:
        target_config['database'] = target_database
    
    recovery = PointInTimeRecovery(config, db_type)
    
    try:
        click.echo(f"Restoring backup {backup_id}...")
        
        if target_config:
            click.echo(f"Target config: {json.dumps(target_config, indent=2)}")
        
        success, msg = recovery.restore_backup(backup_id, target_config if target_config else None)
        
        if success:
            click.echo(click.style("✓ Restore completed successfully!", fg='green'))
        else:
            click.echo(click.style(f"✗ Restore failed: {msg}", fg='red'))
            raise click.Abort()
            
    except Exception as e:
        click.echo(click.style(f"✗ Restore failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('analyze-binlog')
@click.argument('backup_id')
@click.pass_context
def analyze_binlog(ctx, backup_id):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.recovery import PointInTimeRecovery
    recovery = PointInTimeRecovery(config, db_type)
    
    try:
        click.echo(f"Analyzing binlog timeline for backup: {backup_id}")
        
        timestamps = recovery.analyze_binlog_timeline(backup_id)
        
        if not timestamps:
            click.echo("No timestamps found in binlog.")
            return
        
        click.echo(f"\nFound {len(timestamps)} events:\n")
        click.echo(f"{'Index':<6} {'Timestamp':<25} {'Position':<12}")
        click.echo("-" * 60)
        
        for i, ts in enumerate(timestamps[:20], 1):
            click.echo(f"{i:<6} {ts['timestamp']:<25} {ts.get('position', 'N/A'):<12}")
        
        if len(timestamps) > 20:
            click.echo(f"\n... and {len(timestamps) - 20} more events")
        
        click.echo(f"\nTime range:")
        click.echo(f"  First: {timestamps[0]['timestamp']}")
        click.echo(f"  Last:  {timestamps[-1]['timestamp']}")
        
    except Exception as e:
        click.echo(click.style(f"✗ Analysis failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('pitr')
@click.argument('target_time')
@click.option('--full-backup-id', help='Specific full backup to use as base')
@click.pass_context
def point_in_time_recovery(ctx, target_time, full_backup_id):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    recovery = PointInTimeRecovery(config, db_type)
    
    try:
        click.echo(f"Starting point-in-time recovery to {target_time}...")
        
        if full_backup_id:
            click.echo(f"Using base backup: {full_backup_id}")
        
        success, result = recovery.recover_to_point(target_time, full_backup_id)
        
        if success:
            click.echo(click.style("✓ Point-in-time recovery completed!", fg='green'))
            click.echo(f"  Target time: {result['target_time']}")
            click.echo(f"  Full backup: {result['full_backup']}")
            click.echo(f"  Incremental backups applied: {result['incremental_count']}")
        else:
            click.echo(click.style(f"✗ PITR failed: {result}", fg='red'))
            raise click.Abort()
            
    except Exception as e:
        click.echo(click.style(f"✗ PITR failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command()
@click.argument('backup_id')
@click.pass_context
def verify(ctx, backup_id):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.backup import BackupEngine
    engine = BackupEngine(config, db_type)
    verifier = BackupVerifier(config, db_type)
    
    try:
        click.echo(f"Verifying backup {backup_id}...")
        
        backup_info = None
        for b in engine.list_backups():
            if b['backup_id'] == backup_id:
                backup_info = b
                break
        
        if not backup_info:
            click.echo(click.style(f"✗ Backup not found: {backup_id}", fg='red'))
            raise click.Abort()
        
        success, result = verifier.verify_backup(backup_info)
        
        if success:
            click.echo(click.style("✓ Backup verification passed!", fg='green'))
            if isinstance(result, dict):
                click.echo(f"  Verified at: {result['verified_at']}")
                click.echo(f"  Queries passed: {len([q for q in result['queries'] if q['success']])}/{len(result['queries'])}")
        else:
            click.echo(click.style(f"✗ Backup verification failed!", fg='red'))
            click.echo(f"  Error: {result}")
            raise click.Abort()
            
    except Exception as e:
        click.echo(click.style(f"✗ Verification failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('test-connection')
@click.pass_context
def test_connection(ctx):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.database import DatabaseFactory
    db_config = config.get_database_config(db_type)
    connector = DatabaseFactory.get_connector(db_type, db_config)
    
    try:
        click.echo(f"Testing connection to {db_type}...")
        success, msg = connector.test_connection()
        
        if success:
            click.echo(click.style("✓ Connection successful!", fg='green'))
        else:
            click.echo(click.style(f"✗ Connection failed: {msg}", fg='red'))
            raise click.Abort()
            
    except Exception as e:
        click.echo(click.style(f"✗ Connection test failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('storage-health')
@click.pass_context
def storage_health(ctx):
    config = ctx.obj['config']
    
    storage = StorageFactory.get_storage(config.get_storage_config())
    
    try:
        click.echo("Checking storage health...\n")
        
        if hasattr(storage, 'health_check'):
            results = storage.health_check()
            
            for status in results:
                status_icon = click.style("✓", fg='green') if status['success'] else click.style("✗", fg='red')
                status_text = click.style("OK", fg='green') if status['success'] else click.style("FAILED", fg='red')
                click.echo(f"{status_icon} {status['storage']:<15} {status_text}")
                if not status['success']:
                    click.echo(f"    Error: {status['message']}")
            
            available = sum(1 for r in results if r['success'])
            click.echo(f"\n{available}/{len(results)} storage services available")
            
        else:
            click.echo("Health check not supported for this storage type")
            
    except Exception as e:
        click.echo(click.style(f"✗ Health check failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command()
@click.option('--email/--no-email', default=True, help='Send report via email')
@click.pass_context
def report(ctx, email):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.reporting import ReportGenerator
    
    try:
        click.echo("Generating weekly backup report...")
        
        reporter = ReportGenerator(config, db_type)
        report_data, report_path = reporter.generate_weekly_report()
        
        summary = report_data['summary']
        
        click.echo(click.style("\n✓ Report generated successfully!", fg='green'))
        click.echo(f"  Report file: {report_path}")
        
        click.echo(f"\n{'='*50}")
        click.echo(f"Weekly Backup Report - {db_type.upper()}")
        click.echo(f"{'='*50}")
        click.echo(f"Period: {report_data['period']['start'][:10]} to {report_data['period']['end'][:10]}")
        click.echo(f"\nSummary:")
        click.echo(f"  Total backups:    {summary['total_backups']}")
        click.echo(f"  Successful:       {summary['successful']}")
        click.echo(f"  Failed:           {summary['failed']}")
        click.echo(f"  Success rate:     {summary['success_rate']}%")
        click.echo(f"  Full backups:     {summary['full_backups']}")
        click.echo(f"  Incremental:      {summary['incremental_backups']}")
        click.echo(f"  Total data:       {format_size(summary['total_data_bytes'])}")
        
        verification = report_data['verification_results']
        click.echo(f"\nVerification:")
        click.echo(f"  Verified:         {verification['total_verified']}")
        click.echo(f"  Passed:           {verification['passed']}")
        click.echo(f"  Pass rate:        {verification['pass_rate']}%")
        
        trend = report_data['data_trend']
        if trend:
            change_sign = '+' if trend['change_bytes'] >= 0 else ''
            click.echo(f"\nData Trend:")
            click.echo(f"  Start size:       {format_size(trend['start_size_bytes'])}")
            click.echo(f"  End size:         {format_size(trend['end_size_bytes'])}")
            click.echo(f"  Change:           {change_sign}{format_size(trend['change_bytes'])} ({change_sign}{trend['change_percent']}%)")
        
        if email:
            click.echo(f"\nReport email sent to configured recipients")
            
    except Exception as e:
        click.echo(click.style(f"✗ Report generation failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('key-rotate')
@click.option('--new-key', help='Specify new encryption key (auto-generated if not provided)')
@click.option('--re-encrypt/--no-re-encrypt', default=True, help='Re-encrypt historical backups')
@click.pass_context
def key_rotate(ctx, new_key, re_encrypt):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.key_rotation import KeyRotationManager
    
    try:
        click.echo("Starting encryption key rotation...")
        
        manager = KeyRotationManager(config, db_type)
        
        result = manager.rotate_key(new_key=new_key, re_encrypt_history=re_encrypt)
        
        click.echo(click.style("\n✓ Key rotation completed!", fg='green'))
        click.echo(f"  New version: {result['new_version']}")
        click.echo(f"  New key: {result['new_key']}")
        click.echo(f"  Re-encrypted history: {result['re_encrypted']}")
        
        click.echo(click.style("\n⚠️  IMPORTANT: Update the encryption key in your config file!", fg='yellow'))
        
    except Exception as e:
        click.echo(click.style(f"✗ Key rotation failed: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('key-history')
@click.pass_context
def key_history(ctx):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.key_rotation import KeyRotationManager
    
    try:
        manager = KeyRotationManager(config, db_type)
        keys = manager.list_key_history()
        
        if not keys:
            click.echo("No key rotation history found.")
            return
        
        click.echo(f"Found {len(keys)} key(s) in history:\n")
        
        for key in keys:
            status_color = 'green' if key['status'] == 'active' else 'yellow'
            status_text = click.style(key['status'].upper(), fg=status_color)
            
            click.echo(f"Version {key['version']} [{status_text}]")
            click.echo(f"  Created:    {key['created_at']}")
            if key.get('deprecated_at'):
                click.echo(f"  Deprecated: {key['deprecated_at']}")
            click.echo(f"  Key:        {key['key'][:8]}...{key['key'][-4:]}")
            click.echo()
        
        current = manager.get_current_key_info()
        if current:
            click.echo(f"Current active key: version {current['version']}")
        
    except Exception as e:
        click.echo(click.style(f"✗ Failed to get key history: {str(e)}", fg='red'))
        raise click.Abort()


@cli.command('auto-key-check')
@click.option('--rotation-days', type=int, default=30, help='Rotation interval in days')
@click.pass_context
def auto_key_check(ctx, rotation_days):
    config = ctx.obj['config']
    db_type = ctx.obj['db_type']
    
    from dbbackup.key_rotation import KeyRotationManager
    
    try:
        manager = KeyRotationManager(config, db_type)
        
        current = manager.get_current_key_info()
        if current:
            from datetime import datetime
            created_at = datetime.fromisoformat(current['created_at'])
            days_old = (datetime.now() - created_at).days
            click.echo(f"Current key (v{current['version']}) is {days_old} days old")
            click.echo(f"Rotation threshold: {rotation_days} days")
        
        if manager.should_rotate(rotation_days):
            click.echo(click.style("\nKey rotation needed!", fg='yellow'))
            if click.confirm("Perform key rotation now?"):
                result = manager.rotate_key()
                click.echo(click.style(f"✓ Rotated to version {result['new_version']}", fg='green'))
        else:
            click.echo(click.style("\n✓ Key is up to date, no rotation needed", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"✗ Key check failed: {str(e)}", fg='red'))
        raise click.Abort()


if __name__ == '__main__':
    cli()

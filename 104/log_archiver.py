#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import tarfile
import argparse
import configparser
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ArchiveResult:
    def __init__(self, source_dir):
        self.source_dir = source_dir
        self.target_dir = None
        self.success = False
        self.files_found = 0
        self.files_archived = 0
        self.files_deleted = 0
        self.archive_path = None
        self.error = None
        self.filtered_by_content = 0


class LogArchiver:
    def __init__(self, source_dir, target_dir, retention_days=7, compress_level=6,
                 content_filter=None, case_sensitive=False):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.retention_days = max(1, retention_days)
        self.compress_level = max(1, min(9, compress_level))
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
        self.log_pattern = re.compile(r'.*-(\d{4}-\d{2}-\d{2})\.log$')
        self.content_filter = content_filter
        self.case_sensitive = case_sensitive

    def ensure_target_dir(self):
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def parse_log_date(self, filename):
        match = self.log_pattern.match(filename)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return None
        return None

    def check_content_match(self, file_path):
        if not self.content_filter:
            return True
        
        flags = 0 if self.case_sensitive else re.IGNORECASE
        pattern = re.compile(self.content_filter, flags)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if pattern.search(line):
                        return True
        except Exception:
            pass
        return False

    def find_logs_to_archive(self):
        if not self.source_dir.exists():
            return

        with os.scandir(self.source_dir) as entries:
            for entry in entries:
                if entry.is_file(follow_symlinks=False):
                    log_date = self.parse_log_date(entry.name)
                    if log_date and log_date <= self.cutoff_date:
                        yield Path(entry.path)

    def verify_tar_archive(self, tar_path, expected_files):
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                members = tar.getmembers()
                member_names = {m.name for m in members}
                
                for log_file in expected_files:
                    if log_file.name not in member_names:
                        return False
                
                for member in members:
                    try:
                        tar.extractfile(member)
                    except Exception:
                        return False
                
                return True
        except Exception:
            return False

    def compress_logs(self, log_files):
        if not log_files:
            return None, []

        date_str = self.cutoff_date.strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        archive_name = f'logs_archive_{date_str}_{timestamp}.tar.gz'
        final_archive_path = self.target_dir / archive_name
        
        fd, temp_path = tempfile.mkstemp(suffix='.tar.gz', dir=self.target_dir)
        os.close(fd)
        temp_archive_path = Path(temp_path)

        try:
            with tarfile.open(temp_archive_path, f'w:gz', compresslevel=self.compress_level) as tar:
                for log_file in log_files:
                    tar.add(log_file, arcname=log_file.name)

            if not self.verify_tar_archive(temp_archive_path, log_files):
                raise RuntimeError('Archive verification failed')

            temp_archive_path.rename(final_archive_path)
            return final_archive_path, log_files

        except Exception as e:
            if temp_archive_path.exists():
                temp_archive_path.unlink()
            raise RuntimeError(f'Compression failed: {str(e)}')

    def delete_original_logs(self, log_files):
        deleted_count = 0
        for log_file in log_files:
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception:
                pass
        return deleted_count

    def run(self):
        result = ArchiveResult(str(self.source_dir))
        result.target_dir = str(self.target_dir)

        try:
            self.ensure_target_dir()
            
            logs_to_archive = []
            for log_file in self.find_logs_to_archive():
                result.files_found += 1
                if self.check_content_match(log_file):
                    logs_to_archive.append(log_file)
                else:
                    result.filtered_by_content += 1

            if not logs_to_archive:
                result.success = True
                return result

            result.files_archived = len(logs_to_archive)
            archive_path, archived_files = self.compress_logs(logs_to_archive)
            result.archive_path = str(archive_path)
            
            result.files_deleted = self.delete_original_logs(archived_files)
            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False

        return result


class EmailNotifier:
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_password, 
                 from_addr, to_addrs, use_tls=True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        self.to_addrs = to_addrs if isinstance(to_addrs, list) else [to_addrs]
        self.use_tls = use_tls

    def send_report(self, results):
        if not self.to_addrs:
            return False

        total_found = sum(r.files_found for r in results)
        total_archived = sum(r.files_archived for r in results)
        total_deleted = sum(r.files_deleted for r in results)
        total_filtered = sum(r.filtered_by_content for r in results)
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        subject = f'日志归档报告 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        html_body = self._build_html_body(results, total_found, total_archived, 
                                         total_deleted, total_filtered, 
                                         success_count, failed_count)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        
        msg.attach(MIMEText(html_body, 'html'))

        try:
            if self.use_tls:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            server.quit()
            return True
        except Exception:
            return False

    def _build_html_body(self, results, total_found, total_archived, 
                        total_deleted, total_filtered, success_count, failed_count):
        status_color = '#d4edda' if failed_count == 0 else '#f8d7da'
        status_text = '全部成功' if failed_count == 0 else f'{failed_count} 个任务失败'
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {status_color}; padding: 15px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .stat {{ display: inline-block; margin: 10px 20px; padding: 10px; 
                        background-color: #e9ecef; border-radius: 5px; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #dee2e6; padding: 8px; text-align: left; }}
                th {{ background-color: #f8f9fa; }}
                .success {{ color: #28a745; }}
                .error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>日志归档报告 - {status_text}</h2>
                <p>执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="stat">
                    <div class="stat-value">{success_count}/{len(results)}</div>
                    <div>成功任务</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{total_found}</div>
                    <div>找到日志</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{total_archived}</div>
                    <div>已归档</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{total_deleted}</div>
                    <div>已删除</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{total_filtered}</div>
                    <div>被过滤</div>
                </div>
            </div>
            
            <h3>任务详情</h3>
            <table>
                <tr>
                    <th>源目录</th>
                    <th>目标目录</th>
                    <th>状态</th>
                    <th>找到</th>
                    <th>归档</th>
                    <th>删除</th>
                    <th>过滤</th>
                    <th>归档文件</th>
                </tr>
        """
        
        for r in results:
            status_class = 'success' if r.success else 'error'
            status_text = '成功' if r.success else '失败'
            error_note = f'<br><span class="error">错误: {r.error}</span>' if r.error else ''
            archive_path = Path(r.archive_path).name if r.archive_path else '-'
            
            html += f"""
                <tr>
                    <td>{r.source_dir}</td>
                    <td>{r.target_dir}</td>
                    <td class="{status_class}"><strong>{status_text}</strong>{error_note}</td>
                    <td>{r.files_found}</td>
                    <td>{r.files_archived}</td>
                    <td>{r.files_deleted}</td>
                    <td>{r.filtered_by_content}</td>
                    <td>{archive_path}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        return html


def load_yaml_config(config_file):
    if not YAML_AVAILABLE:
        print('Warning: PyYAML not installed, falling back to INI format')
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f'Warning: Error loading YAML config: {e}')
        return None


def load_ini_config(config_file):
    config = configparser.ConfigParser()
    settings = {
        'global': {
            'retention_days': 7,
            'compress_level': 6,
            'content_filter': None,
            'case_sensitive': False
        },
        'directories': [
            {
                'source': '.',
                'target': './archive'
            }
        ],
        'email': None
    }
    
    try:
        if not Path(config_file).exists():
            return settings

        config.read(config_file)
        
        if 'Settings' in config:
            s = config['Settings']
            try:
                settings['global']['retention_days'] = max(1, s.getint('retention_days', 7))
            except (ValueError, TypeError):
                pass
            try:
                settings['global']['compress_level'] = max(1, min(9, s.getint('compress_level', 6)))
            except (ValueError, TypeError):
                pass
            settings['global']['content_filter'] = s.get('content_filter', None) or None
            settings['global']['case_sensitive'] = s.getboolean('case_sensitive', False)
            
            source = s.get('log_dir', '.')
            target = s.get('archive_dir', './archive')
            settings['directories'] = [{'source': source, 'target': target}]
        
        if 'Email' in config:
            e = config['Email']
            settings['email'] = {
                'smtp_host': e.get('smtp_host', ''),
                'smtp_port': e.getint('smtp_port', 465),
                'smtp_user': e.get('smtp_user', ''),
                'smtp_password': e.get('smtp_password', ''),
                'from_addr': e.get('from_addr', ''),
                'to_addrs': [addr.strip() for addr in e.get('to_addrs', '').split(',') if addr.strip()],
                'use_tls': e.getboolean('use_tls', True)
            }
    
    except configparser.Error:
        pass
    
    return settings


def load_config(config_file):
    if not config_file:
        return None
    
    config_path = Path(config_file)
    if not config_path.exists():
        print(f'Warning: Config file {config_file} not found')
        return None
    
    if config_file.endswith(('.yaml', '.yml')):
        yaml_config = load_yaml_config(config_file)
        if yaml_config:
            return parse_yaml_config(yaml_config)
    
    return load_ini_config(config_file)


def parse_yaml_config(yaml_config):
    settings = {
        'global': {
            'retention_days': 7,
            'compress_level': 6,
            'content_filter': None,
            'case_sensitive': False
        },
        'directories': [],
        'email': None
    }
    
    if 'global' in yaml_config:
        g = yaml_config['global']
        settings['global']['retention_days'] = max(1, g.get('retention_days', 7))
        settings['global']['compress_level'] = max(1, min(9, g.get('compress_level', 6)))
        settings['global']['content_filter'] = g.get('content_filter')
        settings['global']['case_sensitive'] = g.get('case_sensitive', False)
    
    if 'directories' in yaml_config and isinstance(yaml_config['directories'], list):
        for dir_pair in yaml_config['directories']:
            if isinstance(dir_pair, dict) and 'source' in dir_pair and 'target' in dir_pair:
                settings['directories'].append({
                    'source': dir_pair['source'],
                    'target': dir_pair['target'],
                    'retention_days': dir_pair.get('retention_days'),
                    'compress_level': dir_pair.get('compress_level'),
                    'content_filter': dir_pair.get('content_filter')
                })
    
    if not settings['directories']:
        settings['directories'] = [{'source': '.', 'target': './archive'}]
    
    if 'email' in yaml_config:
        e = yaml_config['email']
        settings['email'] = {
            'smtp_host': e.get('smtp_host', ''),
            'smtp_port': e.get('smtp_port', 465),
            'smtp_user': e.get('smtp_user', ''),
            'smtp_password': e.get('smtp_password', ''),
            'from_addr': e.get('from_addr', ''),
            'to_addrs': e.get('to_addrs', []),
            'use_tls': e.get('use_tls', True)
        }
    
    return settings


def main():
    parser = argparse.ArgumentParser(description='Server Log Auto Archiver')
    parser.add_argument('--config', '-c', help='Path to configuration file (INI or YAML)')
    parser.add_argument('--log-dir', '-l', help='Directory containing log files')
    parser.add_argument('--archive-dir', '-a', help='Directory to store archived files')
    parser.add_argument('--retention-days', '-d', type=int, help='Number of days to retain logs')
    parser.add_argument('--compress-level', '-z', type=int, choices=range(1, 10),
                        help='GZIP compression level (1-9, default: 6)')
    parser.add_argument('--content-filter', '-f', help='Regex pattern to filter log content')
    parser.add_argument('--case-sensitive', action='store_true', 
                        help='Make content filter case-sensitive')
    parser.add_argument('--no-email', action='store_true', help='Disable email notification')

    args = parser.parse_args()

    config = load_config(args.config) or {}
    global_config = config.get('global', {})
    directories = config.get('directories', [])

    if args.log_dir and args.archive_dir:
        directories = [{
            'source': args.log_dir,
            'target': args.archive_dir,
            'retention_days': args.retention_days,
            'compress_level': args.compress_level,
            'content_filter': args.content_filter
        }]
    elif not directories:
        directories = [{
            'source': args.log_dir or '.',
            'target': args.archive_dir or './archive',
            'retention_days': args.retention_days or 7,
            'compress_level': args.compress_level or 6,
            'content_filter': args.content_filter
        }]

    results = []
    for dir_pair in directories:
        retention_days = dir_pair.get('retention_days') or global_config.get('retention_days', 7)
        compress_level = dir_pair.get('compress_level') or global_config.get('compress_level', 6)
        content_filter = dir_pair.get('content_filter') or args.content_filter or global_config.get('content_filter')
        case_sensitive = args.case_sensitive or global_config.get('case_sensitive', False)

        print(f'\n{"="*60}')
        print(f'处理目录: {dir_pair["source"]}')
        print(f'目标目录: {dir_pair["target"]}')
        print(f'保留天数: {retention_days}')
        print(f'压缩级别: {compress_level}')
        if content_filter:
            print(f'内容过滤: {content_filter}')
        print(f'{"="*60}')

        archiver = LogArchiver(
            source_dir=dir_pair['source'],
            target_dir=dir_pair['target'],
            retention_days=retention_days,
            compress_level=compress_level,
            content_filter=content_filter,
            case_sensitive=case_sensitive
        )
        
        result = archiver.run()
        results.append(result)
        
        if result.success:
            print(f'✓ 成功: 归档 {result.files_archived} 个文件, 删除 {result.files_deleted} 个文件')
            if result.filtered_by_content:
                print(f'  {result.filtered_by_content} 个文件被内容过滤跳过')
        else:
            print(f'✗ 失败: {result.error}')

    email_config = config.get('email')
    if email_config and not args.no_email and email_config.get('smtp_host') and email_config.get('to_addrs'):
        print('\n正在发送邮件报告...')
        notifier = EmailNotifier(**email_config)
        if notifier.send_report(results):
            print('✓ 邮件报告发送成功')
        else:
            print('✗ 邮件报告发送失败')

    print(f'\n{"="*60}')
    success_count = sum(1 for r in results if r.success)
    print(f'全部任务完成: {success_count}/{len(results)} 成功')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()

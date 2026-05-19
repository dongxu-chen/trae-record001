#!/usr/bin/env python3
import re
import json
import os
import glob
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class ProgressBar:
    def __init__(self, total: int, prefix: str = "进度", width: int = 50):
        self.total = total
        self.prefix = prefix
        self.width = width
        self.current = 0

    def update(self, current: int, message: str = ""):
        self.current = current
        percent = int(100 * current / self.total)
        filled = int(self.width * current / self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        suffix = f" {percent}% {message}"
        print(f"\r{self.prefix}: |{bar}|{suffix}", end='', flush=True)

    def finish(self, message: str = "完成"):
        self.update(self.total, message)
        print()


class LogParser:
    LOG_PATTERNS = [
        re.compile(
            r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+'
            r'\[([^\]]+)\]\s+'
            r'"([^"]+)"\s+'
            r'(\d+)\s+'
            r'(\d+)\s+'
            r'"([^"]*)"\s+'
            r'"([^"]*)"\s+'
            r'(\d+\.?\d*)'
        ),
        re.compile(
            r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+'
            r'\[([^\]]+)\]\s+'
            r'"([^"]+)"\s+'
            r'(\d+)\s+'
            r'(\d+)\s+'
            r'"([^"]*)"\s+'
            r'"([^"]*)"'
        )
    ]

    TIME_INPUT_FORMAT = '%d/%b/%Y:%H:%M:%S %z'
    TIME_OUTPUT_FORMAT = '%Y-%m-%d %H:%M:%S'

    @staticmethod
    def format_time(dt: Optional[datetime]) -> str:
        if dt:
            return dt.strftime(LogParser.TIME_OUTPUT_FORMAT)
        return ''

    @staticmethod
    def parse_time(time_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(time_str, LogParser.TIME_INPUT_FORMAT)
        except ValueError:
            return None

    @staticmethod
    def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None

        for pattern in LogParser.LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                has_response_time = len(groups) == 8
                
                ip = groups[0]
                time_str = groups[1]
                request = groups[2]
                status = int(groups[3])
                body_bytes_sent = int(groups[4])
                referer = groups[5]
                user_agent = groups[6]
                response_time = float(groups[7]) if has_response_time else 0.0

                time = LogParser.parse_time(time_str)
                
                method, path, protocol = '', '', ''
                request_parts = request.split()
                if len(request_parts) >= 3:
                    method, path, protocol = request_parts[0], request_parts[1], request_parts[2]
                elif len(request_parts) == 2:
                    method, path = request_parts[0], request_parts[1]
                elif len(request_parts) == 1:
                    method = request_parts[0]

                return {
                    'ip': ip,
                    'time': time,
                    'time_str': LogParser.format_time(time),
                    'hour': time.strftime('%Y-%m-%d %H:00') if time else '',
                    'method': method,
                    'path': path,
                    'protocol': protocol,
                    'status': status,
                    'body_bytes_sent': body_bytes_sent,
                    'referer': referer,
                    'user_agent': user_agent,
                    'response_time': response_time,
                    'raw_line': line
                }
        
        return None

    @staticmethod
    def parse_log_file(file_path: str, progress_callback=None) -> Tuple[List[Dict[str, Any]], int]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"日志文件不存在: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"路径不是文件: {file_path}")

        logs = []
        parse_errors = 0
        
        try:
            total_lines = sum(1 for _ in open(file_path, 'r', encoding='utf-8', errors='ignore'))
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        parsed = LogParser.parse_log_line(line)
                        if parsed:
                            logs.append(parsed)
                        else:
                            parse_errors += 1
                    except Exception:
                        parse_errors += 1
                        continue
                    
                    if progress_callback and line_num % max(1, total_lines // 100) == 0:
                        progress_callback(line_num, total_lines)
        except IOError as e:
            raise IOError(f"读取文件失败: {str(e)}")

        return logs, parse_errors


class StatisticsCalculator:
    @staticmethod
    def calculate_status_stats(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_requests = len(logs)
        status_counter = Counter(log['status'] for log in logs)
        
        status_stats = []
        for status, count in sorted(status_counter.items()):
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            status_stats.append({
                'status_code': status,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        return {
            'total_requests': total_requests,
            'status_distribution': status_stats
        }

    @staticmethod
    def find_top_requests_per_second(logs: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        requests_per_second = defaultdict(int)
        
        for log in logs:
            if log['time']:
                second_key = LogParser.format_time(log['time'])
                requests_per_second[second_key] += 1
        
        sorted_seconds = sorted(
            requests_per_second.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [
            {'time': time, 'request_count': count}
            for time, count in sorted_seconds
        ]

    @staticmethod
    def find_slow_requests(logs: List[Dict[str, Any]], threshold_ms: float = 100.0, top_n: int = 10) -> List[Dict[str, Any]]:
        if not logs:
            return []

        slow_requests = [
            log for log in logs
            if log['response_time'] >= threshold_ms
        ]
        
        slow_requests.sort(
            key=lambda x: x['response_time'],
            reverse=True
        )
        
        top_slow = slow_requests[:top_n]
        
        result = []
        for idx, log in enumerate(top_slow):
            result.append({
                'rank': idx + 1,
                'response_time_ms': round(log['response_time'], 2),
                'method': log['method'],
                'path': log['path'],
                'status': log['status'],
                'ip': log['ip'],
                'time': log['time_str']
            })
        
        return result

    @staticmethod
    def calculate_hourly_trend(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hourly_stats = defaultdict(lambda: {'requests': 0, 'errors': 0, 'total_response_time': 0.0})
        
        for log in logs:
            hour = log['hour']
            if not hour:
                continue
            hourly_stats[hour]['requests'] += 1
            hourly_stats[hour]['total_response_time'] += log['response_time']
            if log['status'] >= 400:
                hourly_stats[hour]['errors'] += 1
        
        trend = []
        for hour, stats in sorted(hourly_stats.items()):
            avg_time = stats['total_response_time'] / stats['requests'] if stats['requests'] > 0 else 0
            error_rate = (stats['errors'] / stats['requests'] * 100) if stats['requests'] > 0 else 0
            trend.append({
                'hour': hour,
                'requests': stats['requests'],
                'errors': stats['errors'],
                'error_rate': round(error_rate, 2),
                'avg_response_time_ms': round(avg_time, 2)
            })
        
        return trend

    @staticmethod
    def calculate_summary(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not logs:
            return {
                'total_requests': 0,
                'total_bytes_transferred': 0,
                'avg_response_time_ms': 0.0,
                'min_response_time_ms': 0.0,
                'max_response_time_ms': 0.0,
                'unique_ips': 0,
                'time_range': {'start': '', 'end': ''}
            }
        
        response_times = [log['response_time'] for log in logs]
        total_bytes = sum(log['body_bytes_sent'] for log in logs)
        
        times = [log['time'] for log in logs if log['time']]
        time_range = {'start': '', 'end': ''}
        if times:
            time_range['start'] = LogParser.format_time(min(times))
            time_range['end'] = LogParser.format_time(max(times))
        
        return {
            'total_requests': len(logs),
            'total_bytes_transferred': total_bytes,
            'avg_response_time_ms': round(sum(response_times) / len(response_times), 2),
            'min_response_time_ms': round(min(response_times), 2),
            'max_response_time_ms': round(max(response_times), 2),
            'unique_ips': len(set(log['ip'] for log in logs)),
            'time_range': time_range
        }


class NginxLogAnalyzer:
    def __init__(self, log_file_paths: List[str]):
        self.log_file_paths = log_file_paths
        self.results = []

    def analyze_single_file(self, file_path: str, show_progress: bool = True) -> Dict[str, Any]:
        file_name = os.path.basename(file_path)
        
        if show_progress:
            print(f"\n正在分析: {file_name}")
            
            def progress_callback(current, total):
                percent = int(100 * current / total)
                print(f"\r  解析中: {percent}% ({current}/{total} 行)", end='', flush=True)
        else:
            progress_callback = None

        try:
            logs, parse_errors = LogParser.parse_log_file(file_path, progress_callback)
            
            if show_progress and progress_callback:
                print(f"\r  解析完成: {len(logs)} 有效行, {parse_errors} 行无法解析")
        except Exception as e:
            if show_progress:
                print(f"\r  解析失败: {str(e)}")
            return {
                'file': file_path,
                'file_name': file_name,
                'error': str(e),
                'success': False
            }
        
        if not logs:
            return {
                'file': file_path,
                'file_name': file_name,
                'error': '没有找到有效的日志条目',
                'success': False
            }
        
        report = {
            'file': file_path,
            'file_name': file_name,
            'analysis_time': datetime.now().strftime(LogParser.TIME_OUTPUT_FORMAT),
            'summary': StatisticsCalculator.calculate_summary(logs),
            'status_code_statistics': StatisticsCalculator.calculate_status_stats(logs),
            'top_requests_per_second': StatisticsCalculator.find_top_requests_per_second(logs, 5),
            'top_slow_requests': StatisticsCalculator.find_slow_requests(logs, 100.0, 10),
            'hourly_trend': StatisticsCalculator.calculate_hourly_trend(logs),
            'parse_errors': parse_errors,
            'success': True
        }
        
        return report

    def analyze_all(self, show_progress: bool = True) -> List[Dict[str, Any]]:
        self.results = []
        total_files = len(self.log_file_paths)
        
        if show_progress:
            print(f"\n{'='*60}")
            print(f"开始分析 {total_files} 个日志文件")
            print(f"{'='*60}")
        
        for idx, file_path in enumerate(self.log_file_paths, 1):
            if show_progress:
                print(f"\n[{idx}/{total_files}] ", end='')
            
            result = self.analyze_single_file(file_path, show_progress)
            self.results.append(result)
        
        return self.results

    def save_individual_reports(self, output_dir: str = 'reports', show_progress: bool = True) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []
        
        if show_progress:
            progress = ProgressBar(len(self.results), "保存单独报告")
        
        for idx, result in enumerate(self.results):
            if result['success']:
                base_name = os.path.splitext(result['file_name'])[0]
                output_file = os.path.join(output_dir, f"{base_name}_report.json")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                saved_files.append(output_file)
            
            if show_progress:
                progress.update(idx + 1, result['file_name'])
        
        if show_progress:
            progress.finish()
        
        return saved_files

    def generate_comparison_report(self) -> Dict[str, Any]:
        successful_results = [r for r in self.results if r['success']]
        
        if not successful_results:
            return {
                'error': '没有成功分析的文件可用于对比',
                'total_files': len(self.results),
                'successful_files': 0
            }
        
        files_comparison = []
        all_requests_trend = defaultdict(dict)
        
        for result in successful_results:
            summary = result['summary']
            files_comparison.append({
                'file_name': result['file_name'],
                'file_path': result['file'],
                'total_requests': summary['total_requests'],
                'total_bytes': summary['total_bytes_transferred'],
                'avg_response_time_ms': summary['avg_response_time_ms'],
                'error_count': sum(s['count'] for s in result['status_code_statistics']['status_distribution'] if s['status_code'] >= 400),
                'unique_ips': summary['unique_ips'],
                'time_range': summary['time_range']
            })
            
            for hour_data in result['hourly_trend']:
                hour = hour_data['hour']
                all_requests_trend[hour][result['file_name']] = {
                    'requests': hour_data['requests'],
                    'error_rate': hour_data['error_rate']
                }
        
        sorted_hours = sorted(all_requests_trend.keys())
        trend_analysis = []
        for hour in sorted_hours:
            trend_analysis.append({
                'hour': hour,
                'files': all_requests_trend[hour]
            })
        
        files_comparison_sorted = sorted(files_comparison, key=lambda x: x['total_requests'], reverse=True)
        
        if len(files_comparison_sorted) >= 2:
            first_file = files_comparison_sorted[0]
            second_file = files_comparison_sorted[1]
            request_diff = first_file['total_requests'] - second_file['total_requests']
            request_diff_pct = (request_diff / second_file['total_requests'] * 100) if second_file['total_requests'] > 0 else 0
        else:
            request_diff = 0
            request_diff_pct = 0
        
        total_requests_all = sum(f['total_requests'] for f in files_comparison)
        
        comparison_report = {
            'analysis_time': datetime.now().strftime(LogParser.TIME_OUTPUT_FORMAT),
            'summary': {
                'total_files_analyzed': len(self.results),
                'successful_files': len(successful_results),
                'failed_files': len(self.results) - len(successful_results),
                'total_requests_all_files': total_requests_all,
                'max_requests_file': files_comparison_sorted[0] if files_comparison_sorted else None,
                'min_requests_file': files_comparison_sorted[-1] if files_comparison_sorted else None,
                'top_two_request_diff': request_diff,
                'top_two_request_diff_pct': round(request_diff_pct, 2)
            },
            'files_comparison': files_comparison_sorted,
            'hourly_trend_comparison': trend_analysis
        }
        
        return comparison_report

    def save_comparison_report(self, output_file: str = 'comparison_report.json') -> bool:
        report = self.generate_comparison_report()
        
        try:
            output_dir = os.path.dirname(os.path.abspath(output_file))
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False


def print_comparison_summary(report: Dict[str, Any]):
    if 'error' in report:
        print(f"\n对比报告错误: {report['error']}")
        return
    
    print(f"\n{'='*60}")
    print("汇总对比报告")
    print(f"{'='*60}")
    
    summary = report['summary']
    print(f"\n📊 分析概览")
    print(f"  总文件数: {summary['total_files_analyzed']}")
    print(f"  成功分析: {summary['successful_files']}")
    print(f"  失败文件: {summary['failed_files']}")
    print(f"  总请求数: {summary['total_requests_all_files']:,}")
    
    print(f"\n📈 文件请求量排名")
    for idx, file_info in enumerate(report['files_comparison'], 1):
        print(f"  {idx}. {file_info['file_name']}: {file_info['total_requests']:,} 请求")
        print(f"     平均响应: {file_info['avg_response_time_ms']}ms | 唯一IP: {file_info['unique_ips']}")
    
    if len(report['files_comparison']) >= 2:
        print(f"\n📉 请求量变化趋势 (Top 2)")
        top1 = report['files_comparison'][0]
        top2 = report['files_comparison'][1]
        diff = top1['total_requests'] - top2['total_requests']
        pct = (diff / top2['total_requests'] * 100) if top2['total_requests'] > 0 else 0
        print(f"  {top1['file_name']} vs {top2['file_name']}: {diff:+} 请求 ({pct:+.2f}%)")
    
    print(f"\n⏰ 每小时趋势对比 (前5小时)")
    for hour_data in report['hourly_trend_comparison'][:5]:
        hour = hour_data['hour']
        file_reqs = [f"{fname}: {data['requests']}" for fname, data in hour_data['files'].items()]
        print(f"  {hour}: {', '.join(file_reqs)}")


def expand_file_patterns(patterns: List[str]) -> List[str]:
    files = []
    for pattern in patterns:
        if os.path.isdir(pattern):
            files.extend(glob.glob(os.path.join(pattern, '*.log')))
        elif '*' in pattern or '?' in pattern:
            files.extend(glob.glob(pattern))
        else:
            files.append(pattern)
    
    seen = set()
    unique_files = []
    for f in files:
        abs_path = os.path.abspath(f)
        if abs_path not in seen and os.path.isfile(f):
            seen.add(abs_path)
            unique_files.append(f)
    
    return sorted(unique_files)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python nginx_log_analyzer.py <日志文件1> [日志文件2] ... [选项]")
        print("支持通配符和目录:")
        print("  python nginx_log_analyzer.py *.log")
        print("  python nginx_log_analyzer.py logs/")
        print("  python nginx_log_analyzer.py access.log error.log")
        print("\n选项:")
        print("  --output-dir <目录>    指定报告输出目录 (默认: reports)")
        print("  --no-progress          关闭进度显示")
        sys.exit(1)
    
    args = sys.argv[1:]
    output_dir = 'reports'
    show_progress = True
    file_patterns = []
    
    i = 0
    while i < len(args):
        if args[i] == '--output-dir' and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == '--no-progress':
            show_progress = False
            i += 1
        else:
            file_patterns.append(args[i])
            i += 1
    
    log_files = expand_file_patterns(file_patterns)
    
    if not log_files:
        print("错误: 没有找到匹配的日志文件")
        sys.exit(1)
    
    if show_progress:
        print(f"找到 {len(log_files)} 个日志文件:")
        for f in log_files[:5]:
            print(f"  - {os.path.basename(f)}")
        if len(log_files) > 5:
            print(f"  ... 还有 {len(log_files) - 5} 个文件")
    
    analyzer = NginxLogAnalyzer(log_files)
    results = analyzer.analyze_all(show_progress)
    
    if show_progress:
        print(f"\n{'='*60}")
        print("分析完成")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if r['success'])
        print(f"\n成功: {successful}/{len(results)}")
        
        if successful == 0:
            print("没有文件成功分析，无法生成报告")
            sys.exit(1)
    
    saved_reports = analyzer.save_individual_reports(output_dir, show_progress)
    if show_progress:
        print(f"\n已生成 {len(saved_reports)} 个单独报告到目录: {output_dir}/")
    
    comparison_file = os.path.join(output_dir, 'comparison_report.json')
    if analyzer.save_comparison_report(comparison_file):
        if show_progress:
            print(f"已生成汇总对比报告: {comparison_file}")
            print_comparison_summary(analyzer.generate_comparison_report())
    else:
        if show_progress:
            print("无法生成汇总对比报告")
    
    if show_progress:
        print(f"\n{'='*60}")
        print("全部任务完成!")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()

import os
import sys
import subprocess
import webbrowser

from report import get_report_path, get_latest_report, cleanup_old_reports
from test_api import APITestRunner


def collect_test_results():
    runner = APITestRunner()
    results = runner.run_all_tests()
    return results


def run_tests():
    script_dir = os.path.dirname(__file__)
    report_path = get_report_path()

    cleanup_old_reports(keep_count=20)

    cmd = [
        sys.executable, "-m", "pytest",
        os.path.join(script_dir, "test_api.py"),
        "-v",
        f"--html={report_path}",
        "--self-contained-html"
    ]

    print(f"开始运行测试...")
    print(f"报告将保存到: {report_path}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=script_dir)
    exit_code = result.returncode

    print("-" * 60)
    if exit_code == 0:
        print("测试执行成功！")
    else:
        print(f"测试执行完成，退出码: {exit_code}")

    try:
        test_results = collect_test_results()
    except Exception as e:
        print(f"收集测试结果失败: {e}")
        test_results = []

    latest_report = get_latest_report()
    if latest_report and os.path.exists(latest_report):
        print(f"\n查看报告: {latest_report}")

        try:
            from slack_notify import slack_notifier
            sent = slack_notifier.send_notification(test_results, latest_report)
            if sent:
                print("Slack 通知已发送")
        except Exception as e:
            print(f"Slack 通知发送失败: {e}")

        try:
            webbrowser.open(f"file://{latest_report}")
        except Exception as e:
            print(f"自动打开报告失败: {e}")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())

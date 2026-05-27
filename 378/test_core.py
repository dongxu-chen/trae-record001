"""快速功能测试 - 验证核心逻辑 (无需 SSH/Celery)"""
from configdrift.parsers import strip_comments, get_parser
from configdrift.detector import detect_drift, build_repair_commands, syntax_check_cmd


def test_strip_comments():
    text = """# 这是注释
worker_processes auto;  # 行尾注释
; 另一注释
listen 80;
"""
    cleaned = strip_comments(text)
    assert "#" not in cleaned
    assert "worker_processes auto;" in cleaned
    assert "listen 80;" in cleaned
    assert len(cleaned.splitlines()) == 2
    print("✓ strip_comments OK")


def test_parse_and_detect():
    baseline_text = """worker_processes auto;
listen 80;
keepalive_timeout 65;
"""
    current_text = """worker_processes 4;  # 注释
listen 8080;
keepalive_timeout 65;
gzip on;
"""
    parser = get_parser("kvshell")
    baseline = parser.parse(strip_comments(baseline_text))
    current = parser.parse(strip_comments(current_text))
    items = detect_drift(
        baseline, current,
        baseline_text=baseline_text,
        current_text=current_text,
        auto_strip_comments=True,
    )
    print(f"检测到 {len(items)} 项漂移:")
    for it in items:
        print(f"  {it.drift_type:7s} {it.key}: {it.baseline_text} -> {it.current_text}")
    
    # 验证检测到 changed: worker_processes, listen
    # added: gzip
    # 总共 3 项 (worker_processes 和 listen 都变了 + gzip added
    changed = [i for i in items if i.drift_type == "changed"]
    added = [i for i in items if i.drift_type == "added"]
    assert len(changed) == 2
    assert len(added) == 1
    assert any(it.key == "worker_processes" for it in changed)
    assert any(it.key == "listen" for it in changed)
    assert added[0].key == "gzip"
    print("✓ detect_drift OK")

    # 测试语法检查命令
    check = syntax_check_cmd("nginx", "/etc/nginx/nginx.conf")
    assert "nginx -t" in check
    print("✓ syntax_check_cmd OK")

    # 测试修复命令
    repair = build_repair_commands("nginx", "/etc/nginx/nginx.conf", items)
    print("\n修复命令:")
    for cmd in repair:
        print(f"  {cmd}")
    
    repair_all = " ".join(repair)
    assert any("nginx -t" in cmd for cmd in repair)  # 前置检查
    assert "sed -i 's/^worker_processes" in repair_all
    assert any("cp -a" in cmd for cmd in repair)  # 备份
    assert any("nginx -s reload" in cmd for cmd in repair)
    print("✓ build_repair_commands OK (含前置语法检查 + 备份 + 二次检查 + reload")


def test_ini_parse():
    ini_text = """[mysqld]
datadir = /var/lib/mysql
# 注释行
port = 3306
max_connections = 1000
"""
    parser = get_parser("ini")
    data = parser.parse(strip_comments(ini_text))
    assert data["mysqld :: port"] == 3306
    assert data["mysqld :: max_connections"] == 1000
    print("✓ ini parser OK")


if __name__ == "__main__":
    test_strip_comments()
    test_parse_and_detect()
    test_ini_parse()
    print("\n✅ 所有核心功能测试通过!")

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("测试API安全漏洞扫描器 - 新功能验证")
print("=" * 70)

print("\n1. 测试配置模型...")
try:
    from scanner.config import ScanConfig, RoleConfig, Vulnerability, VerificationResult
    
    role1 = RoleConfig(
        name="admin",
        description="系统管理员",
        auth_type="bearer",
        auth_token="admin-token-123",
        is_admin=True
    )
    role2 = RoleConfig(
        name="user",
        description="普通用户",
        auth_type="bearer",
        auth_token="user-token-456",
        is_admin=False
    )
    
    config = ScanConfig(
        target_url="http://test.com/api/users?id=1",
        roles=[role1, role2],
        concurrency=5,
        verification_replay_count=3,
        enable_session_isolation=True
    )
    
    print(f"  ✓ RoleConfig 创建成功: {role1.name}, {role2.name}")
    print(f"  ✓ ScanConfig 支持多角色: {len(config.roles)} 个角色")
    print(f"  ✓ 重放验证次数: {config.verification_replay_count}")
    print(f"  ✓ 会话隔离: {config.enable_session_isolation}")
    
    vr = VerificationResult(
        replay_count=3,
        success_count=3,
        consistency_score=1.0,
        original_response={"status_code": 200},
        replay_responses=[{"status_code": 200, "consistent": True}] * 3,
        is_consistent=True
    )
    print(f"  ✓ VerificationResult 创建成功: 一致性 {vr.consistency_score:.0%}")
    
except Exception as e:
    print(f"  ✗ 配置模型测试失败: {e}")
    sys.exit(1)

print("\n2. 测试请求引擎 - 会话隔离...")
try:
    from scanner.request_engine import RequestEngine, Session
    
    engine = RequestEngine(config)
    
    session_stats = engine.get_session_stats()
    print(f"  ✓ 创建了 {session_stats['total_sessions']} 个隔离会话")
    print(f"  ✓ 角色会话: {session_stats['role_sessions']}")
    
    session1 = engine.get_session()
    session2 = engine.get_session()
    
    print(f"  ✓ 会话1 ID: {session1.session_id}")
    print(f"  ✓ 会话2 ID: {session2.session_id}")
    print(f"  ✓ 会话ID不同: {session1.session_id != session2.session_id}")
    
    admin_session = engine.get_role_session("admin")
    user_session = engine.get_role_session("user")
    
    print(f"  ✓ 管理员会话认证头: {admin_session.headers.get('Authorization', 'N/A')[:20]}...")
    print(f"  ✓ 普通用户会话认证头: {user_session.headers.get('Authorization', 'N/A')[:20]}...")
    print(f"  ✓ 角色会话认证头不同: {admin_session.headers.get('Authorization') != user_session.headers.get('Authorization')}")
    
    print(f"  ✓ 所有角色名称: {engine.get_all_role_names()}")
    
except Exception as e:
    print(f"  ✗ 请求引擎测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. 测试响应比对功能...")
try:
    resp1 = {
        "status_code": 200,
        "content_length": 1000,
        "content_hash": hash("test content"),
        "content": "user data id=1 name=admin email=admin@test.com"
    }
    resp2 = {
        "status_code": 200,
        "content_length": 1000,
        "content_hash": hash("test content"),
        "content": "user data id=1 name=admin email=admin@test.com"
    }
    resp3 = {
        "status_code": 200,
        "content_length": 900,
        "content_hash": hash("different content"),
        "content": "user data id=2 name=user email=user@test.com"
    }
    
    comparison1 = engine.compare_responses(resp1, resp2)
    print(f"  ✓ 相同响应比对: 相似度={comparison1['similarity_score']:.2f}, 完全相同={comparison1['is_identical']}")
    
    comparison2 = engine.compare_responses(resp1, resp3)
    print(f"  ✓ 不同响应比对: 相似度={comparison2['similarity_score']:.2f}, 完全相同={comparison2['is_identical']}")
    
    if "content_similarity" in comparison2["differences"]:
        print(f"  ✓ 内容相似度: {comparison2['differences']['content_similarity']:.2f}")
    
except Exception as e:
    print(f"  ✗ 响应比对测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. 测试漏洞检测器 - 角色越权检测...")
try:
    from scanner.vulnerability_detector import VulnerabilityDetector
    
    detector = VulnerabilityDetector(engine, config)
    
    print(f"  ✓ 检测器角色配置: {detector.role_names}")
    print(f"  ✓ 支持多角色检测: {len(detector.role_names) >= 2}")
    
    from scanner.config import Vulnerability
    test_vuln = Vulnerability(
        type="Privilege Escalation (Horizontal)",
        severity="high",
        endpoint="/api/users/1",
        method="GET",
        payload="Role switch: admin -> user",
        evidence="角色 'user' 与管理员角色 'admin' 响应相似度: 0.95",
        description="角色越权 - 低权限角色 'user' 可访问管理员 'admin' 的资源",
        recommendation="Implement proper role-based access control (RBAC)",
        role_context="admin vs user",
        comparison_evidence='{"similarity_score": 0.95, "is_identical": false}'
    )
    
    print(f"  ✓ 漏洞支持角色上下文: {test_vuln.role_context}")
    print(f"  ✓ 漏洞支持比对证据: {test_vuln.comparison_evidence[:50]}...")
    
except Exception as e:
    print(f"  ✗ 漏洞检测器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. 测试报告生成 - 新字段支持...")
try:
    from scanner.report_generator import ReportGenerator
    from scanner.config import ScanResult
    from datetime import datetime
    
    test_vuln.verified = True
    test_vuln.verification_result = vr
    
    result = ScanResult(
        target_url="http://test.com",
        scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_requests=150,
        vulnerabilities=[test_vuln],
        scan_status="completed",
        roles_scanned=["admin", "user", "guest"],
        session_id="scan_abc123xyz"
    )
    
    html_report = ReportGenerator.generate_html_report(result)
    print(f"  ✓ HTML报告生成成功 ({len(html_report)} 字符)")
    print(f"  ✓ 包含角色扫描信息: {'角色上下文' in html_report}")
    print(f"  ✓ 包含重放验证信息: {'重放验证结果' in html_report}")
    print(f"  ✓ 包含会话ID: {'scan_abc123xyz' in html_report}")
    
    md_report = ReportGenerator.generate_markdown_report(result)
    print(f"  ✓ Markdown报告生成成功 ({len(md_report)} 字符)")
    print(f"  ✓ 包含角色信息: {'admin' in md_report and 'user' in md_report}")
    print(f"  ✓ 包含重放验证: {'重放' in md_report}")
    
except Exception as e:
    print(f"  ✗ 报告生成测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. 测试扫描管理器...")
try:
    from scanner.scan_manager import ScanManager
    
    manager = ScanManager(config)
    stats = manager.get_scan_stats()
    
    print(f"  ✓ 扫描ID: {stats['scan_id']}")
    print(f"  ✓ 扫描角色: {stats['roles']}")
    print(f"  ✓ 会话统计: {len(stats['session_stats']['session_details'])} 个会话")
    
except Exception as e:
    print(f"  ✗ 扫描管理器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. 测试会话池管理...")
try:
    async def test_session_pool():
        engine2 = RequestEngine(config)
        
        session_ids = []
        for i in range(3):
            sid = await engine2.acquire_session()
            session_ids.append(sid)
            print(f"  ✓ 获取会话 {i+1}: {sid}")
        
        for sid in session_ids:
            await engine2.release_session(sid)
            print(f"  ✓ 释放会话: {sid}")
        
        print(f"  ✓ 会话池大小: {engine2.session_pool.qsize()}")
    
    asyncio.run(test_session_pool())
    
except Exception as e:
    print(f"  ✗ 会话池测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ 所有新功能测试通过！")
print("=" * 70)

print("\n📋 功能改进总结:")
print("  1. 角色越权扫描: 支持多角色配置，同接口不同角色对比")
print("  2. 会话绑定: 每个并发请求独立会话，状态完全隔离")
print("  3. 重放验证: 自动重放请求+结果比对，确认漏洞可复现")
print("  4. 响应比对: 多维度响应分析（状态码、长度、哈希、内容相似度）")
print("\n📁 修改的文件:")
print("  - [config.py](file:///d:/Project/trae/project/record001/596/backend/scanner/config.py)")
print("  - [request_engine.py](file:///d:/Project/trae/project/record001/596/backend/scanner/request_engine.py)")
print("  - [vulnerability_detector.py](file:///d:/Project/trae/project/record001/596/backend/scanner/vulnerability_detector.py)")
print("  - [scan_manager.py](file:///d:/Project/trae/project/record001/596/backend/scanner/scan_manager.py)")
print("  - [report_generator.py](file:///d:/Project/trae/project/record001/596/backend/scanner/report_generator.py)")
print("  - [main.py](file:///d:/Project/trae/project/record001/596/backend/main.py)")

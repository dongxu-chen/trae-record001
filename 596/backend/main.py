from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from typing import List, Optional
from pydantic import BaseModel
import asyncio
import json

from scanner.config import (
    ScanConfig, ScanResult, RoleConfig, VerificationResult,
    VulnerabilityStatus, StatusUpdateRequest, Comment, ExploitResult,
    VulnerabilityFilter, VulnerabilityRecord
)
from scanner.scan_manager import ScanManager
from scanner.vulnerability_manager import VulnerabilityManager
from scanner.report_generator import ReportGenerator

app = FastAPI(title="API安全漏洞扫描器", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_scans = {}
scan_results = {}
vuln_manager = VulnerabilityManager()


class MultipleScanRequest(BaseModel):
    config: ScanConfig
    endpoints: List[str]


class BulkStatusUpdate(BaseModel):
    vuln_ids: List[str]
    status: VulnerabilityStatus
    comment: Optional[str] = None
    author: Optional[str] = None


class AssignRequest(BaseModel):
    assignee: str
    author: Optional[str] = None


class TagsRequest(BaseModel):
    tags: List[str]
    author: Optional[str] = None


@app.post("/api/scan", response_model=ScanResult)
async def start_scan(config: ScanConfig):
    try:
        scan_id = f"scan_{len(active_scans) + 1}"
        
        endpoints = [config.target_url] if "?" not in config.target_url else [config.target_url]
        
        scan_manager = ScanManager(config)
        active_scans[scan_id] = scan_manager
        
        result = await scan_manager.scan(endpoints)
        scan_results[scan_id] = result
        
        del active_scans[scan_id]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan/multiple")
async def start_multiple_scan(request: MultipleScanRequest):
    try:
        scan_manager = ScanManager(request.config)
        result = await scan_manager.scan(request.endpoints)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan/with-roles", response_model=ScanResult)
async def start_scan_with_roles(config: ScanConfig):
    try:
        if not config.roles or len(config.roles) < 2:
            raise HTTPException(
                status_code=400, 
                detail="请至少配置2个角色以启用角色越权检测"
            )
        
        scan_id = f"scan_{len(active_scans) + 1}"
        endpoints = [config.target_url] if "?" not in config.target_url else [config.target_url]
        
        scan_manager = ScanManager(config)
        active_scans[scan_id] = scan_manager
        
        result = await scan_manager.scan(endpoints)
        scan_results[scan_id] = result
        
        del active_scans[scan_id]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vulnerabilities")
async def list_vulnerabilities(
    status: Optional[List[VulnerabilityStatus]] = Query(None),
    severity: Optional[List[str]] = Query(None),
    vuln_type: Optional[List[str]] = Query(None),
    assignee: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tags: Optional[List[str]] = Query(None)
):
    filter_params = VulnerabilityFilter(
        status=status,
        severity=severity,
        vuln_type=vuln_type,
        assignee=assignee,
        date_from=date_from,
        date_to=date_to,
        tags=tags
    )
    records = vuln_manager.list_vulnerabilities(filter_params)
    return {
        "total": len(records),
        "vulnerabilities": records
    }


@app.get("/api/vulnerabilities/{vuln_id}")
async def get_vulnerability(vuln_id: str):
    record = vuln_manager.get_vulnerability(vuln_id)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.get("/api/vulnerabilities/{vuln_id}/lifecycle")
async def get_vulnerability_lifecycle(vuln_id: str):
    summary = vuln_manager.get_lifecycle_summary(vuln_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return summary


@app.patch("/api/vulnerabilities/{vuln_id}/status")
async def update_vulnerability_status(vuln_id: str, request: StatusUpdateRequest):
    record = vuln_manager.update_status(vuln_id, request)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.post("/api/vulnerabilities/bulk/status")
async def bulk_update_status(request: BulkStatusUpdate):
    status_request = StatusUpdateRequest(
        status=request.status,
        comment=request.comment,
        author=request.author
    )
    result = vuln_manager.bulk_update_status(request.vuln_ids, status_request)
    return result


@app.patch("/api/vulnerabilities/{vuln_id}/assign")
async def assign_vulnerability(vuln_id: str, request: AssignRequest):
    record = vuln_manager.assign_vulnerability(vuln_id, request.assignee, request.author)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.post("/api/vulnerabilities/{vuln_id}/comments")
async def add_vulnerability_comment(vuln_id: str, comment: Comment):
    record = vuln_manager.add_comment(vuln_id, comment)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.post("/api/vulnerabilities/{vuln_id}/tags")
async def add_vulnerability_tags(vuln_id: str, request: TagsRequest):
    record = vuln_manager.add_tags(vuln_id, request.tags, request.author)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.delete("/api/vulnerabilities/{vuln_id}/tags")
async def remove_vulnerability_tags(vuln_id: str, request: TagsRequest):
    record = vuln_manager.remove_tags(vuln_id, request.tags, request.author)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.patch("/api/vulnerabilities/{vuln_id}/fix")
async def update_fix_info(vuln_id: str, fix_commit: Optional[str] = None, fix_date: Optional[str] = None):
    record = vuln_manager.update_fix_info(vuln_id, fix_commit, fix_date)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.patch("/api/vulnerabilities/{vuln_id}/exploit")
async def set_exploit_result(vuln_id: str, exploit_result: ExploitResult):
    record = vuln_manager.set_exploit_result(vuln_id, exploit_result)
    if not record:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return record


@app.delete("/api/vulnerabilities/{vuln_id}")
async def delete_vulnerability(vuln_id: str, author: Optional[str] = None):
    success = vuln_manager.delete_vulnerability(vuln_id, author)
    if not success:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return {"success": True, "message": "Vulnerability deleted"}


@app.get("/api/vulnerabilities/statistics/summary")
async def get_vulnerability_statistics():
    return vuln_manager.get_statistics()


@app.get("/api/vulnerabilities/export")
async def export_vulnerabilities(
    vuln_ids: Optional[List[str]] = Query(None),
    format: str = Query("json", description="json or csv")
):
    try:
        content = vuln_manager.export_vulnerabilities(vuln_ids, format)
        if format == "csv":
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=vulnerabilities.csv"}
            )
        return JSONResponse(content=json.loads(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/vulnerabilities/statuses")
async def get_vulnerability_statuses():
    return {
        "statuses": [
            {"id": "new", "name": "新建", "color": "#ff4444"},
            {"id": "confirmed", "name": "已确认", "color": "#ff8800"},
            {"id": "in_progress", "name": "修复中", "color": "#ffbb33"},
            {"id": "fixed", "name": "已修复", "color": "#00C851"},
            {"id": "verified", "name": "已验证", "color": "#007E33"},
            {"id": "closed", "name": "已关闭", "color": "#999999"},
            {"id": "reopened", "name": "已重新打开", "color": "#ff4444"}
        ]
    }


@app.get("/api/report/{scan_id}/json")
async def get_json_report(scan_id: str):
    if scan_id not in scan_results:
        raise HTTPException(status_code=404, detail="Scan not found")
    return JSONResponse(content=scan_results[scan_id].dict())


@app.get("/api/report/{scan_id}/html")
async def get_html_report(scan_id: str):
    if scan_id not in scan_results:
        raise HTTPException(status_code=404, detail="Scan not found")
    html_content = ReportGenerator.generate_html_report(scan_results[scan_id])
    return HTMLResponse(content=html_content)


@app.post("/api/report/generate/html")
async def generate_html_report(result: ScanResult):
    html_content = ReportGenerator.generate_html_report(result)
    return HTMLResponse(content=html_content)


@app.post("/api/report/generate/markdown")
async def generate_markdown_report(result: ScanResult):
    return {"markdown": ReportGenerator.generate_markdown_report(result)}


@app.get("/api/payloads/{payload_type}")
async def get_payloads(payload_type: str):
    import os
    payloads_dir = os.path.join(os.path.dirname(__file__), "payloads")
    filepath = os.path.join(payloads_dir, f"{payload_type}.txt")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Payload type not found")
    
    with open(filepath, "r", encoding="utf-8") as f:
        payloads = [line.strip() for line in f if line.strip()]
    
    return {"payload_type": payload_type, "count": len(payloads), "payloads": payloads}


@app.get("/api/scan/types")
async def get_scan_types():
    return {
        "scan_types": [
            {"id": "sql_injection", "name": "SQL注入", "description": "检测SQL注入漏洞"},
            {"id": "xxe", "name": "XXE注入", "description": "检测XML外部实体注入漏洞"},
            {"id": "idor", "name": "IDOR", "description": "检测不安全直接对象引用漏洞"},
            {"id": "privilege_escalation", "name": "越权访问", "description": "检测权限提升和越权访问漏洞（支持多角色对比）"},
            {"id": "business_logic", "name": "业务逻辑漏洞", "description": "检测订单负数、金额溢出、状态篡改等业务逻辑漏洞"}
        ]
    }


@app.get("/api/auth/types")
async def get_auth_types():
    return {
        "auth_types": [
            {"id": "none", "name": "无认证"},
            {"id": "bearer", "name": "Bearer Token"},
            {"id": "basic", "name": "Basic Auth"},
            {"id": "custom", "name": "自定义头部"}
        ]
    }


@app.get("/api/features")
async def get_features():
    return {
        "features": [
            {
                "id": "role_based_scan",
                "name": "角色越权扫描",
                "description": "同接口不同角色对比，检测水平/垂直越权",
                "enabled": True
            },
            {
                "id": "session_isolation",
                "name": "会话隔离",
                "description": "并发请求会话绑定，请求状态完全隔离",
                "enabled": True
            },
            {
                "id": "replay_verification",
                "name": "重放验证",
                "description": "自动重放+结果比对，确认漏洞可复现",
                "enabled": True
            },
            {
                "id": "response_comparison",
                "name": "响应比对",
                "description": "多维度响应内容相似度分析",
                "enabled": True
            },
            {
                "id": "business_logic",
                "name": "业务逻辑漏洞检测",
                "description": "检测订单负数、金额溢出、状态篡改、批量赋值等漏洞",
                "enabled": True
            },
            {
                "id": "exploit_verification",
                "name": "漏洞利用验证",
                "description": "尝试实际利用漏洞获取敏感数据，验证漏洞可利用性",
                "enabled": True
            },
            {
                "id": "vulnerability_lifecycle",
                "name": "漏洞全生命周期管理",
                "description": "漏洞创建、确认、分配、修复、验证、关闭全流程追踪",
                "enabled": True
            }
        ]
    }


@app.get("/api/scan/{scan_id}/stats")
async def get_scan_stats(scan_id: str):
    if scan_id not in active_scans:
        raise HTTPException(status_code=404, detail="Scan not found or not active")
    
    scan_manager = active_scans[scan_id]
    return scan_manager.get_scan_stats()


@app.get("/api/verification/example")
async def get_verification_example():
    return VerificationResult(
        replay_count=3,
        success_count=3,
        consistency_score=1.0,
        original_response={"status_code": 200, "content_length": 1234, "content_hash": "abc123"},
        replay_responses=[
            {"status_code": 200, "content_length": 1234, "content_hash": "abc123", "consistent": True},
            {"status_code": 200, "content_length": 1234, "content_hash": "abc123", "consistent": True},
            {"status_code": 200, "content_length": 1234, "content_hash": "abc123", "consistent": True}
        ],
        is_consistent=True
    )


@app.get("/api/roles/example")
async def get_roles_example():
    return {
        "example": {
            "roles": [
                {
                    "name": "admin",
                    "description": "系统管理员",
                    "auth_type": "bearer",
                    "auth_token": "admin-jwt-token-here",
                    "is_admin": True
                },
                {
                    "name": "user",
                    "description": "普通用户",
                    "auth_type": "bearer",
                    "auth_token": "user-jwt-token-here",
                    "is_admin": False
                },
                {
                    "name": "guest",
                    "description": "访客用户",
                    "auth_type": "none",
                    "is_admin": False
                }
            ]
        }
    }


@app.get("/api/business_logic/example")
async def get_business_logic_example():
    return {
        "example": {
            "test_cases": [
                {"field": "quantity", "value": -1, "desc": "商品数量负数"},
                {"field": "price", "value": -100, "desc": "价格负数"},
                {"field": "amount", "value": 0, "desc": "金额为0"},
                {"field": "total", "value": 0.0000001, "desc": "金额极小值"},
                {"field": "status", "value": "approved", "desc": "状态篡改"},
                {"field": "role", "value": "admin", "desc": "角色篡改"}
            ],
            "payloads_file": "payloads/business_logic.txt"
        }
    }


@app.get("/api/exploit/example")
async def get_exploit_example():
    return ExploitResult(
        exploit_type="SQL Injection",
        success=True,
        data_extracted=[
            {"type": "email", "data": "admin@example.com", "payload": "' UNION SELECT..."},
            {"type": "username", "data": "admin", "payload": "' UNION SELECT..."},
            {"type": "credit_card", "data": "4111-xxxx-xxxx-1111", "payload": "' UNION SELECT..."}
        ],
        evidence="成功从数据库提取敏感用户数据"
    )


@app.get("/")
async def root():
    return {
        "name": "API安全漏洞扫描器",
        "version": "3.0.0",
        "docs": "/docs",
        "new_features": [
            "✨ 角色越权扫描: 同接口多角色对比检测",
            "✨ 会话隔离: 并发请求状态完全隔离",
            "✨ 重放验证: 自动重放确认漏洞复现",
            "✨ 响应比对: 多维度内容相似度分析",
            "✨ 业务逻辑漏洞检测: 订单负数、金额溢出、状态篡改",
            "✨ 漏洞利用验证: 实际利用漏洞提取敏感数据",
            "✨ 漏洞生命周期管理: 创建→确认→修复→验证→关闭"
        ],
        "endpoints": {
            "扫描API": [
                "POST /api/scan - 启动单个端点扫描",
                "POST /api/scan/multiple - 启动多个端点扫描",
                "POST /api/scan/with-roles - 启动带角色配置的扫描",
                "GET /api/scan/{scan_id}/stats - 获取扫描状态统计"
            ],
            "漏洞管理API": [
                "GET /api/vulnerabilities - 漏洞列表（支持筛选）",
                "GET /api/vulnerabilities/{id} - 漏洞详情",
                "GET /api/vulnerabilities/{id}/lifecycle - 漏洞生命周期时间线",
                "PATCH /api/vulnerabilities/{id}/status - 更新漏洞状态",
                "POST /api/vulnerabilities/bulk/status - 批量更新状态",
                "PATCH /api/vulnerabilities/{id}/assign - 分配漏洞",
                "POST /api/vulnerabilities/{id}/comments - 添加评论",
                "POST /api/vulnerabilities/{id}/tags - 添加标签",
                "DELETE /api/vulnerabilities/{id}/tags - 移除标签",
                "PATCH /api/vulnerabilities/{id}/fix - 更新修复信息",
                "PATCH /api/vulnerabilities/{id}/exploit - 设置利用结果",
                "DELETE /api/vulnerabilities/{id} - 删除漏洞",
                "GET /api/vulnerabilities/statistics/summary - 漏洞统计",
                "GET /api/vulnerabilities/export - 导出漏洞数据",
                "GET /api/vulnerabilities/statuses - 获取状态列表"
            ],
            "报告API": [
                "GET /api/report/{scan_id}/json - JSON格式报告",
                "GET /api/report/{scan_id}/html - HTML格式报告",
                "POST /api/report/generate/html - 生成HTML报告",
                "POST /api/report/generate/markdown - 生成Markdown报告"
            ],
            "辅助API": [
                "GET /api/payloads/{type} - 获取漏洞载荷",
                "GET /api/scan/types - 扫描类型列表",
                "GET /api/auth/types - 认证类型列表",
                "GET /api/features - 功能特性列表",
                "GET /api/roles/example - 角色配置示例",
                "GET /api/business_logic/example - 业务逻辑检测示例",
                "GET /api/exploit/example - 漏洞利用示例",
                "GET /api/verification/example - 验证结果示例"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    import json
    uvicorn.run(app, host="0.0.0.0", port=8000)

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.config.config import settings
from backend.core.scan_manager import ScanManager
from backend.reports.report_generator import ReportGenerator

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    
    if settings.TRIVY_DB_AUTO_UPDATE:
        logger.info("Starting Trivy DB auto-update service...")
        try:
            await scan_manager.start_db_auto_update()
            logger.info("Trivy DB auto-update service started successfully")
        except Exception as e:
            logger.error(f"Failed to start Trivy DB auto-update: {e}")
    
    yield
    
    logger.info("Shutting down application...")
    try:
        await scan_manager.stop_db_auto_update()
        logger.info("Trivy DB auto-update service stopped")
    except Exception as e:
        logger.error(f"Error stopping Trivy DB auto-update: {e}")

app = FastAPI(
    title="Docker Image Security Scanner API",
    description="Docker镜像安全扫描工具 - 支持CVE漏洞扫描、敏感文件检测、配置风险检查",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scan_manager = ScanManager()
report_generator = ReportGenerator(reports_dir=settings.REPORTS_DIR)

class ScanRequest(BaseModel):
    images: List[str] = Field(..., description="要扫描的Docker镜像名称列表")
    scan_types: Optional[List[str]] = Field(
        default=["vulnerabilities", "secrets", "rules"],
        description="扫描类型: vulnerabilities, secrets, rules"
    )
    generate_reports: Optional[bool] = Field(
        default=True,
        description="是否生成报告文件"
    )
    report_formats: Optional[List[str]] = Field(
        default=["json", "html", "junit"],
        description="报告格式: json, html, junit"
    )
    fail_on_severity: Optional[str] = Field(
        default=None,
        description="达到指定严重程度时返回失败: CRITICAL, HIGH, MEDIUM, LOW"
    )

class DBUpdateRequest(BaseModel):
    force: bool = Field(default=False, description="是否强制更新")

class OfflineDBRequest(BaseModel):
    path: str = Field(..., description="离线数据库文件路径")

class ScanJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

@app.get("/")
async def root():
    return {
        "name": "Docker Image Security Scanner API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/status")
async def get_scanner_status():
    return scan_manager.get_scanner_status()

@app.post("/api/scan", response_model=ScanJobResponse, status_code=202)
async def create_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if not request.images:
        raise HTTPException(status_code=400, detail="至少需要指定一个镜像")
    
    try:
        job_id = await scan_manager.create_scan_job(
            image_names=request.images,
            scan_types=request.scan_types
        )
        
        if request.generate_reports:
            background_tasks.add_task(
                _generate_reports_background,
                job_id,
                request.report_formats
            )
        
        return ScanJobResponse(
            job_id=job_id,
            status="accepted",
            message=f"扫描任务已创建，共 {len(request.images)} 个镜像"
        )
    except Exception as e:
        logger.error(f"创建扫描任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scan/{job_id}")
async def get_scan_status(job_id: str):
    status = scan_manager.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    return status

@app.get("/api/scan/{job_id}/results")
async def get_scan_results(job_id: str):
    results = scan_manager.get_job_results(job_id)
    if not results:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    
    if results["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"扫描尚未完成，当前状态: {results['status']}"
        )
    
    return results

@app.get("/api/jobs")
async def list_jobs(limit: int = 100):
    return scan_manager.list_jobs(limit=limit)

@app.post("/api/scan/{job_id}/cancel")
async def cancel_scan(job_id: str):
    success = await scan_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消该任务")
    return {"message": "任务已取消"}

@app.get("/api/reports")
async def list_reports():
    return report_generator.get_report_list()

@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    filepath = os.path.join(settings.REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )

@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    success = report_generator.delete_report(filename)
    if not success:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"message": "报告已删除"}

@app.post("/api/scan/{job_id}/reports")
async def generate_report(job_id: str, report_type: str = "html"):
    results = scan_manager.get_job_results(job_id)
    if not results:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    
    if results["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"扫描尚未完成，当前状态: {results['status']}"
        )
    
    try:
        if report_type == "json":
            filepath = report_generator.generate_json_report(results)
        elif report_type == "html":
            filepath = report_generator.generate_html_report(results)
        elif report_type == "junit":
            filepath = report_generator.generate_junit_report(results)
        else:
            raise HTTPException(status_code=400, detail="不支持的报告类型，支持: json, html, junit")
        
        filename = os.path.basename(filepath)
        return {
            "message": "报告生成成功",
            "filename": filename,
            "download_url": f"/api/reports/{filename}"
        }
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/status")
async def get_db_status():
    return await scan_manager.get_trivy_db_status()

@app.post("/api/db/update")
async def update_db(request: DBUpdateRequest):
    result = await scan_manager.update_trivy_db(force=request.force)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "更新失败"))
    return result

@app.post("/api/db/auto-update/start")
async def start_db_auto_update():
    result = await scan_manager.start_db_auto_update()
    return result

@app.post("/api/db/auto-update/stop")
async def stop_db_auto_update():
    result = await scan_manager.stop_db_auto_update()
    return result

@app.post("/api/db/export")
async def export_offline_db(request: OfflineDBRequest):
    result = await scan_manager.export_trivy_db(request.path)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "导出失败"))
    return result

@app.post("/api/db/import")
async def import_offline_db(request: OfflineDBRequest):
    result = await scan_manager.import_trivy_db(request.path)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "导入失败"))
    return result

@app.get("/api/rules")
async def list_rules():
    return scan_manager.rules_engine.list_rules()

async def _generate_reports_background(job_id: str, report_formats: List[str] = None):
    try:
        import asyncio
        await asyncio.sleep(1)
        
        results = scan_manager.get_job_results(job_id)
        if results and results["status"] == "completed":
            if not report_formats:
                report_formats = ["json", "html", "junit"]
            
            if "json" in report_formats:
                report_generator.generate_json_report(results)
                logger.info(f"JSON报告生成完成: {job_id}")
            
            if "html" in report_formats:
                report_generator.generate_html_report(results)
                logger.info(f"HTML报告生成完成: {job_id}")
            
            if "junit" in report_formats:
                report_generator.generate_junit_report(results)
                logger.info(f"JUnit报告生成完成: {job_id}")
                
    except Exception as e:
        logger.error(f"后台生成报告失败: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

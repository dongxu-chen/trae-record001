import io
import json
import os
import tempfile
import time
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models.schemas import (
    ResumeData,
    JobDescription,
    MatchResult,
    InterviewQuestion,
    ScreeningResponse,
    TalentPoolRecord,
    DedupResult,
    TalentPoolResponse,
    FunnelAnalysisResponse,
    CompetitorResponse,
)
from app.parser.resume_parser import ResumeParser
from app.parser.nlp_processor import NLPProcessor
from app.matcher.scorer import MatchScorer
from app.matcher.interview import InterviewQuestionGenerator
from app.matcher.talent_pool import TalentPool
from app.matcher.funnel_analyzer import FunnelAnalyzer
from app.matcher.competitor_analyzer import CompetitorAnalyzer

app = FastAPI(
    title="招聘简历智能筛选系统",
    description="基于 NLP 和 BERT 的简历-岗位匹配与智能筛选",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

resume_parser = ResumeParser()
nlp_processor = NLPProcessor()
match_scorer = MatchScorer(nlp_processor)
interview_generator = InterviewQuestionGenerator()
talent_pool = TalentPool()
funnel_analyzer = FunnelAnalyzer()
competitor_analyzer = CompetitorAnalyzer()


class ParseResponse(BaseModel):
    success: bool
    data: Optional[ResumeData] = None
    error: Optional[str] = None


class ScreenRequest(BaseModel):
    resumes: List[dict] = Field(..., description="简历数据列表")
    job: JobDescription = Field(..., description="岗位描述")


@app.get("/")
def root():
    return {
        "service": "招聘简历智能筛选系统 API",
        "version": "1.0.0",
        "endpoints": {
            "POST /parse": "解析单个简历文件",
            "POST /screen": "批量筛选简历并排名",
            "POST /parse-multi": "批量解析简历文件",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/parse", response_model=ParseResponse)
async def parse_resume(
    file: UploadFile = File(..., description="简历文件（PDF/DOCX/TXT）"),
):
    try:
        content = await file.read()
        resume_data = resume_parser.parse_bytes(content, file.filename)
        return ParseResponse(success=True, data=resume_data)
    except Exception as e:
        return ParseResponse(success=False, error=str(e))


@app.post("/parse-multi", response_model=List[ParseResponse])
async def parse_resumes(
    files: List[UploadFile] = File(..., description="简历文件列表"),
):
    results = []
    for file in files:
        try:
            content = await file.read()
            resume_data = resume_parser.parse_bytes(content, file.filename)
            results.append(ParseResponse(success=True, data=resume_data))
        except Exception as e:
            results.append(ParseResponse(success=False, error=str(e)))
    return results


@app.post("/screen", response_model=ScreeningResponse)
async def screen_resumes(request: ScreenRequest):
    try:
        resumes = []
        for r in request.resumes:
            resumes.append(ResumeData(**r))

        results = match_scorer.rank_candidates(resumes, request.job)

        for i, result in enumerate(results):
            if i < len(resumes):
                resume = resumes[i]
                questions = interview_generator.generate_questions(
                    result, resume, request.job
                )
                result.interview_questions = questions

        return ScreeningResponse(
            job_title=request.job.title,
            total_candidates=len(results),
            ranked_results=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen-files")
async def screen_from_files(
    files: List[UploadFile] = File(..., description="简历文件列表"),
    job_title: str = Form(..., description="岗位名称"),
    job_description: str = Form(..., description="岗位描述"),
    required_skills: str = Form(default="", description="技能要求（逗号分隔）"),
    min_education: str = Form(default="本科", description="最低学历"),
    min_experience_years: int = Form(default=0, description="最低工作年限"),
):
    try:
        resumes = []
        parse_errors = []
        for file in files:
            try:
                content = await file.read()
                resume_data = resume_parser.parse_bytes(content, file.filename)
                resumes.append(resume_data)
            except Exception as e:
                parse_errors.append(f"{file.filename}: {str(e)}")

        skills_list = [s.strip() for s in required_skills.split(",") if s.strip()]
        job = JobDescription(
            title=job_title,
            description=job_description,
            required_skills=skills_list,
            min_education=min_education,
            min_experience_years=min_experience_years,
        )

        results = match_scorer.rank_candidates(resumes, job)

        for i, result in enumerate(results):
            if i < len(resumes):
                questions = interview_generator.generate_questions(
                    result, resumes[i], job
                )
                result.interview_questions = questions

        return {
            "job_title": job_title,
            "total_candidates": len(results),
            "parse_errors": parse_errors,
            "ranked_results": [r.model_dump() for r in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo")
async def run_demo():
    sample_job = JobDescription(
        title="高级Python后端开发工程师",
        description="""
        我们正在寻找一名经验丰富的高级Python后端开发工程师，负责核心系统的设计与开发。
        要求：
        1. 精通Python语言，熟悉Django/FastAPI框架
        2. 熟悉MySQL、Redis、MongoDB等数据库
        3. 有Docker、Kubernetes部署经验
        4. 了解微服务架构，有高并发系统设计经验
        5. 具备良好的团队协作能力和沟通能力
        """,
        required_skills=["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "Kubernetes"],
        min_education="本科",
        min_experience_years="3年以上",
    )

    sample_resumes = [
        ResumeData(
            candidate_name="张三",
            phone="13800138001",
            email="zhangsan@example.com",
            skills=["python", "django", "fastapi", "mysql", "redis", "docker", "kubernetes", "mongodb", "linux", "git"],
            work_experience=[
                {
                    "start_date": "2021年",
                    "end_date": "至今",
                    "company": "某科技公司",
                    "position": "高级后端开发",
                    "description": "负责电商平台后端开发，使用Python/Django/FastAPI，MySQL数据库，Redis缓存，Docker部署，Kubernetes集群管理。",
                }
            ],
            education=[
                {
                    "start_date": "2015年",
                    "end_date": "2019年",
                    "school": "某重点大学",
                    "level": "本科",
                    "major": "计算机科学与技术",
                    "description": "计算机科学与技术专业，本科学历",
                }
            ],
            projects=[
                {
                    "name": "电商平台重构项目",
                    "description": "使用FastAPI重构核心服务，MySQL数据库优化，Redis缓存策略，Docker容器化部署，K8s集群管理，QPS提升300%",
                    "technologies": ["fastapi", "mysql", "redis", "docker", "kubernetes"],
                }
            ],
            full_text="""
            张三 13800138001 zhangsan@example.com
            技能: Python, Django, FastAPI, MySQL, Redis, MongoDB, Docker, Kubernetes, Linux, Git
            工作经历: 2021年-至今 某科技公司 高级后端开发
            负责电商平台后端开发，使用Python/Django/FastAPI，MySQL数据库，Redis缓存，Docker部署，Kubernetes集群管理。
            教育背景: 2015年-2019年 某重点大学 计算机科学与技术 本科
            项目经验: 电商平台重构项目 - 使用FastAPI重构核心服务，MySQL数据库优化，Redis缓存策略，Docker容器化部署，K8s集群管理，QPS提升300%
            """,
        ),
        ResumeData(
            candidate_name="李四",
            phone="13900139002",
            email="lisi@example.com",
            skills=["java", "spring", "mysql", "redis", "docker", "linux", "git"],
            work_experience=[
                {
                    "start_date": "2020年",
                    "end_date": "至今",
                    "company": "某互联网公司",
                    "position": "后端开发",
                    "description": "使用Java/Spring Boot开发后端服务，MySQL数据库，Redis缓存，Docker部署。",
                }
            ],
            education=[
                {
                    "start_date": "2016年",
                    "end_date": "2020年",
                    "school": "某普通大学",
                    "level": "本科",
                    "major": "软件工程",
                    "description": "软件工程专业，本科学历",
                }
            ],
            projects=[
                {
                    "name": "用户中心系统",
                    "description": "使用Spring Boot开发用户中心，MySQL数据库，Redis缓存",
                    "technologies": ["spring", "mysql", "redis"],
                }
            ],
            full_text="""
            李四 13900139002 lisi@example.com
            技能: Java, Spring, MySQL, Redis, Docker, Linux, Git
            工作经历: 2020年-至今 某互联网公司 后端开发
            使用Java/Spring Boot开发后端服务，MySQL数据库，Redis缓存，Docker部署。
            教育背景: 2016年-2020年 某普通大学 软件工程 本科
            项目经验: 用户中心系统 - 使用Spring Boot开发用户中心，MySQL数据库，Redis缓存
            """,
        ),
        ResumeData(
            candidate_name="王五",
            phone="13700137003",
            email="wangwu@example.com",
            skills=["python", "django", "fastapi", "mysql", "redis", "docker", "kubernetes", "tensorflow", "pytorch", "mongodb", "elasticsearch", "linux", "git"],
            work_experience=[
                {
                    "start_date": "2018年",
                    "end_date": "至今",
                    "company": "某AI公司",
                    "position": "资深后端开发/架构师",
                    "description": "负责AI平台后端架构设计，Python/FastAPI微服务开发，MySQL/MongoDB数据库，Redis/Elasticsearch缓存，Docker/K8s部署，TensorFlow/PyTorch模型服务化。",
                },
                {
                    "start_date": "2016年",
                    "end_date": "2018年",
                    "company": "某科技公司",
                    "position": "后端开发",
                    "description": "Python/Django后端开发，MySQL数据库，Redis缓存",
                }
            ],
            education=[
                {
                    "start_date": "2013年",
                    "end_date": "2016年",
                    "school": "某知名大学",
                    "level": "硕士",
                    "major": "人工智能",
                    "description": "人工智能专业，硕士研究生",
                }
            ],
            projects=[
                {
                    "name": "AI智能推荐平台",
                    "description": "基于FastAPI的推荐系统后端，TensorFlow模型服务，Redis缓存，ES搜索引擎，Docker/K8s部署",
                    "technologies": ["fastapi", "tensorflow", "redis", "elasticsearch", "docker", "kubernetes"],
                },
                {
                    "name": "大数据分析平台",
                    "description": "Python后端服务，MongoDB数据存储，Docker容器化，K8s编排",
                    "technologies": ["python", "mongodb", "docker", "kubernetes"],
                }
            ],
            full_text="""
            王五 13700137003 wangwu@example.com
            技能: Python, Django, FastAPI, MySQL, Redis, MongoDB, Elasticsearch, Docker, Kubernetes, TensorFlow, PyTorch, Linux, Git
            工作经历:
            2018年-至今 某AI公司 资深后端开发/架构师
            负责AI平台后端架构设计，Python/FastAPI微服务开发，MySQL/MongoDB数据库，Redis/Elasticsearch缓存，Docker/K8s部署，TensorFlow/PyTorch模型服务化。
            2016年-2018年 某科技公司 后端开发
            Python/Django后端开发，MySQL数据库，Redis缓存。
            教育背景: 2013年-2016年 某知名大学 人工智能 硕士
            项目经验:
            AI智能推荐平台 - 基于FastAPI的推荐系统后端，TensorFlow模型服务，Redis缓存，ES搜索引擎，Docker/K8s部署
            大数据分析平台 - Python后端服务，MongoDB数据存储，Docker容器化，K8s编排
            """,
        ),
    ]

    results = match_scorer.rank_candidates(sample_resumes, sample_job)
    for i, result in enumerate(results):
        if i < len(sample_resumes):
            questions = interview_generator.generate_questions(
                result, sample_resumes[i], sample_job
            )
            result.interview_questions = questions

    return ScreeningResponse(
        job_title=sample_job.title,
        total_candidates=len(results),
        ranked_results=results,
    )


class TalentPoolAddRequest(BaseModel):
    resume: ResumeData
    source: Optional[str] = None
    force_add: bool = False


class TalentPoolSearchRequest(BaseModel):
    keyword: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    limit: int = 100


class FunnelStageUpdateRequest(BaseModel):
    job_title: str
    candidate_id: str
    stage_code: str
    duration_days: Optional[float] = None


class FunnelImportRequest(BaseModel):
    job_title: str
    stage_counts: Dict[str, int]


@app.post("/talent/check-duplicate", response_model=DedupResult)
async def check_duplicate(resume: ResumeData):
    return talent_pool.check_duplicate(resume)


@app.post("/talent/add")
async def add_to_talent_pool(request: TalentPoolAddRequest):
    record, dedup = talent_pool.add_record(
        resume=request.resume,
        source=request.source,
        force=request.force_add,
    )
    return {
        "success": True,
        "record": record.model_dump(),
        "dedup_result": dedup.model_dump(),
    }


@app.post("/talent/batch-add")
async def batch_add_to_talent_pool(
    files: List[UploadFile] = File(..., description="简历文件列表"),
    source: Optional[str] = Form(default=None),
    skip_duplicate: bool = Form(default=True),
):
    results = []
    for file in files:
        try:
            content = await file.read()
            resume_data = resume_parser.parse_bytes(content, file.filename)
            record, dedup = talent_pool.add_record(
                resume=resume_data,
                source=source or file.filename,
                force=not skip_duplicate,
            )
            results.append({
                "filename": file.filename,
                "success": True,
                "record_id": record.record_id,
                "is_duplicate": dedup.is_duplicate,
                "confidence": dedup.confidence,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })
    return {"total": len(files), "results": results}


@app.post("/talent/search", response_model=TalentPoolResponse)
async def search_talent_pool(request: TalentPoolSearchRequest):
    records = talent_pool.search_records(
        keyword=request.keyword,
        skills=request.skills,
        tags=request.tags,
        status=request.status,
        limit=request.limit,
    )
    stats = talent_pool.get_statistics()
    return TalentPoolResponse(
        total_records=stats["total_records"],
        active_records=stats["active_records"],
        recent_additions=stats["recent_additions_7d"],
        records=records,
    )


@app.get("/talent/stats")
async def get_talent_pool_stats():
    return talent_pool.get_statistics()


@app.get("/talent/{record_id}")
async def get_talent_record(record_id: str):
    record = talent_pool.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.patch("/talent/{record_id}/status")
async def update_talent_status(record_id: str, status: str):
    success = talent_pool.update_record_status(record_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"success": True, "record_id": record_id, "new_status": status}


@app.post("/funnel/update-stage")
async def update_funnel_stage(request: FunnelStageUpdateRequest):
    funnel_analyzer.add_candidate_stage(
        job_title=request.job_title,
        candidate_id=request.candidate_id,
        stage_code=request.stage_code,
        duration_days=request.duration_days,
    )
    return {"success": True, "message": "Stage updated"}


@app.post("/funnel/import")
async def import_funnel_data(request: FunnelImportRequest):
    funnel_analyzer.import_existing_data(
        job_title=request.job_title,
        stage_counts=request.stage_counts,
    )
    return {"success": True, "message": "Data imported"}


@app.get("/funnel/analyze/{job_title}", response_model=FunnelAnalysisResponse)
async def analyze_funnel(job_title: str):
    return funnel_analyzer.analyze_funnel(job_title)


@app.get("/funnel/stages")
async def get_funnel_stages():
    return {"stages": funnel_analyzer.get_stage_definitions()}


@app.post("/competitor/add-candidate")
async def add_competitor_candidate(resume: ResumeData, match_score: float = 0.0):
    competitor_analyzer.add_candidate(resume, match_score)
    return {"success": True}


@app.post("/competitor/batch-analyze")
async def batch_analyze_competitors(
    files: List[UploadFile] = File(..., description="简历文件列表"),
):
    for file in files:
        try:
            content = await file.read()
            resume_data = resume_parser.parse_bytes(content, file.filename)
            competitor_analyzer.add_candidate(resume_data, 0.0)
        except Exception:
            pass
    return competitor_analyzer.analyze()


@app.get("/competitor/analyze", response_model=CompetitorResponse)
async def analyze_competitors(top_n: int = 10):
    return competitor_analyzer.analyze(top_n=top_n)


@app.get("/competitor/companies")
async def get_competitor_companies():
    return {"companies": competitor_analyzer.get_company_list()}


@app.post("/competitor/clear")
async def clear_competitor_data():
    competitor_analyzer.clear_data()
    return {"success": True, "message": "Competitor data cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
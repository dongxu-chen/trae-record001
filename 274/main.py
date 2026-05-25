from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from search_service import EcommerceSearchService

app = FastAPI(
    title="电商搜索意图识别系统",
    description="基于BERT、知识图谱和Elasticsearch的电商搜索意图识别系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_service = EcommerceSearchService(use_pretrained=False)


class SearchRequest(BaseModel):
    query: str
    top_n: Optional[int] = 10


class IntentAnalysisRequest(BaseModel):
    query: str


class AttributeExtractionRequest(BaseModel):
    query: str


class QueryRewriteRequest(BaseModel):
    query: str


@app.get("/")
async def root():
    return {
        "message": "电商搜索意图识别系统 API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "综合搜索接口",
            "/intent": "意图识别接口",
            "/attributes": "属性抽取接口",
            "/rewrite": "查询改写接口",
            "/stats": "系统统计信息",
            "/docs": "API文档"
        }
    }


@app.post("/search")
async def search(request: SearchRequest):
    try:
        result = search_service.search(request.query, top_n=request.top_n)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intent")
async def analyze_intent(request: IntentAnalysisRequest):
    try:
        result = search_service.analyze_intent(request.query)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/attributes")
async def extract_attributes(request: AttributeExtractionRequest):
    try:
        result = search_service.extract_attributes(request.query)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rewrite")
async def rewrite_query(request: QueryRewriteRequest):
    try:
        result = search_service.rewrite_query(request.query)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    try:
        stats = search_service.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products")
async def get_products():
    try:
        products = search_service.product_search.get_all_products()
        return {
            "success": True,
            "data": {
                "total": len(products),
                "products": products
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List, Optional

from .models.schemas import (
    SummarizeRequest,
    SummarizeResponse,
    HealthResponse,
    FactCheckInfo,
    TopicAwareSummary,
    TopicSummary,
    QualityEvaluation,
    RougeScores,
    MultiDocSummarizeRequest,
    MultiDocSummarizeResponse,
    DocContribution,
    EvaluateRequest,
    EvaluateResponse
)
from .services.abstractive_summarizer import AbstractiveSummarizer
from .services.extractive_summarizer import ExtractiveSummarizer
from .services.multi_doc_summarizer import MultiDocSummarizer
from .utils.language_detector import LanguageDetector
from .utils.keyword_extractor import KeywordExtractor
from .utils.fact_checker import FactChecker
from .utils.topic_extractor import TopicExtractor
from .utils.rouge_evaluator import SummaryQualityEvaluator


app = FastAPI(
    title="Text Summarization API",
    description="Multi-language text summarization with BART/T5 models, sliding window, factuality checking, topic segmentation, multi-doc summarization, and ROUGE quality evaluation",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

abstractive_summarizer = AbstractiveSummarizer()
extractive_summarizer = ExtractiveSummarizer()
multi_doc_summarizer = MultiDocSummarizer()
language_detector = LanguageDetector()
keyword_extractor = KeywordExtractor()
fact_checker = FactChecker(number_tolerance=0.05)
topic_extractor = TopicExtractor(max_topics=5)
quality_evaluator = SummaryQualityEvaluator()


@app.on_event("startup")
async def startup_event():
    print("Starting Text Summarization Service v3.0...")
    abstractive_summarizer.load_bart()
    print("Service ready!")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        models_loaded=abstractive_summarizer.loaded_models
    )


def _evaluate_quality(
    summary: str,
    source_text: str,
    reference_summary: Optional[str] = None
) -> QualityEvaluation:
    eval_result = quality_evaluator.comprehensive_evaluate(
        summary,
        source_text,
        reference_summary
    )
    
    return QualityEvaluation(
        rouge_scores=RougeScores(
            rouge1=round(eval_result.rouge_scores.rouge1, 4),
            rouge2=round(eval_result.rouge_scores.rouge2, 4),
            rougel=round(eval_result.rouge_scores.rougel, 4),
            rouge1_precision=round(eval_result.rouge_scores.rouge1_precision, 4),
            rouge2_precision=round(eval_result.rouge_scores.rouge2_precision, 4),
            rougel_precision=round(eval_result.rouge_scores.rougel_precision, 4),
            rouge1_recall=round(eval_result.rouge_scores.rouge1_recall, 4),
            rouge2_recall=round(eval_result.rouge_scores.rouge2_recall, 4),
            rougel_recall=round(eval_result.rouge_scores.rougel_recall, 4)
        ),
        factual_consistency=round(eval_result.factual_consistency, 4),
        relevance_score=round(eval_result.relevance_score, 4),
        coverage_score=round(eval_result.coverage_score, 4),
        overall_score=round(eval_result.overall_score, 4),
        overall_quality=quality_evaluator.get_quality_label(eval_result.overall_score),
        key_points_covered=eval_result.key_points_covered,
        missing_key_points=eval_result.missing_key_points
    )


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    try:
        original_length = len(request.text)
        
        lang_code = request.language
        if not lang_code:
            lang_code, _ = language_detector.detect_language(request.text)
        
        key_phrases = keyword_extractor.extract_keywords(request.text, top_k=10)
        
        if request.summary_type == "abstractive":
            summary, chunks_processed = abstractive_summarizer.summarize(
                text=request.text,
                model_type=request.model,
                max_length=request.max_length,
                min_length=request.min_length,
                preserve_keywords=request.preserve_keywords,
                language=lang_code,
                enable_sliding_window=request.enable_sliding_window
            )
        else:
            summary, chunks_processed = extractive_summarizer.summarize(
                text=request.text,
                num_sentences=request.extractive_sentences,
                method="textrank",
                preserve_keywords=request.preserve_keywords,
                enable_sliding_window=request.enable_sliding_window
            )
        
        corrected_summary = None
        fact_check_info = None
        
        if request.enable_fact_check:
            fact_result = fact_checker.check(
                source_text=request.text,
                summary_text=summary,
                auto_correct=request.auto_correct
            )
            
            if fact_result.corrections:
                corrected_summary = fact_result.corrected_summary
            
            fact_check_info = FactCheckInfo(
                is_consistent=fact_result.is_consistent,
                number_issues=fact_result.number_issues,
                entity_issues=fact_result.entity_issues,
                corrections=fact_result.corrections
            )
        
        topic_summary_info = None
        if request.enable_topic_segmentation:
            def topic_summarizer_fn(text, **kwargs):
                try:
                    result = abstractive_summarizer.summarize(
                        text=text,
                        model_type=request.model,
                        max_length=kwargs.get('max_length', 100),
                        min_length=kwargs.get('min_length', 30),
                        preserve_keywords=True,
                        enable_sliding_window=False
                    )
                    return result[0] if isinstance(result, tuple) else result
                except:
                    return text[:100]
            
            topic_result = topic_extractor.generate_topic_aware_summary(
                text=request.text,
                summarizer_fn=topic_summarizer_fn,
                method=request.topic_method,
                num_topics=request.num_topics,
                max_length=100,
                min_length=30
            )
            
            topic_summaries = [
                TopicSummary(
                    topic_id=t['topic_id'],
                    keywords=t['keywords'],
                    topic_summary=t['topic_summary'],
                    topic_text=t['topic_text'],
                    num_sentences=t['num_sentences']
                )
                for t in topic_result['topics']
            ]
            
            topic_summary_info = TopicAwareSummary(
                topics=topic_summaries,
                num_topics=topic_result['num_topics'],
                method=topic_result['method']
            )
        
        display_summary = corrected_summary if corrected_summary else summary
        summary_length = len(display_summary)
        compression_ratio = (original_length - summary_length) / original_length if original_length > 0 else 0
        
        quality_eval = None
        if request.enable_fact_check:
            quality_eval = _evaluate_quality(display_summary, request.text)
        
        return SummarizeResponse(
            summary=summary,
            corrected_summary=corrected_summary,
            original_length=original_length,
            summary_length=summary_length,
            summary_type=request.summary_type,
            model=request.model if request.summary_type == "abstractive" else "textrank",
            language=lang_code,
            key_phrases=key_phrases,
            compression_ratio=round(compression_ratio, 4),
            chunks_processed=chunks_processed,
            fact_check=fact_check_info,
            topic_summary=topic_summary_info,
            quality_evaluation=quality_eval
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multi-doc-summarize", response_model=MultiDocSummarizeResponse)
async def multi_doc_summarize(request: MultiDocSummarizeRequest):
    try:
        if request.summary_type == "abstractive":
            result = multi_doc_summarizer.summarize_abstractive(
                documents=request.documents,
                abstractive_summarizer=abstractive_summarizer,
                model_type=request.model,
                max_length=request.max_length,
                min_length=100,
                intermediate_summary_length=150
            )
        else:
            result = multi_doc_summarizer.summarize_extractive(
                documents=request.documents,
                num_sentences=request.num_sentences,
                method='mmr'
            )
        
        doc_contributions = [
            DocContribution(
                doc_id=dc['doc_id'],
                sentences_used=dc['sentences_used'],
                total_sentences=dc['total_sentences']
            )
            for dc in result.get('doc_contributions', [])
        ]
        
        combined_docs = "\n\n".join(request.documents)
        quality_eval = None
        if request.enable_quality_eval and result.get('summary'):
            quality_eval = _evaluate_quality(result['summary'], combined_docs)
        
        return MultiDocSummarizeResponse(
            summary=result['summary'],
            summary_type=request.summary_type,
            num_docs=result['num_docs'],
            model=result.get('model'),
            doc_contributions=doc_contributions,
            intermediate_summaries=result.get('intermediate_summaries'),
            quality_evaluation=quality_eval
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multi-doc-summarize-files", response_model=MultiDocSummarizeResponse)
async def multi_doc_summarize_files(
    files: List[UploadFile] = File(...),
    summary_type: str = Form("extractive"),
    model: str = Form("bart"),
    max_length: int = Form(300),
    num_sentences: int = Form(8),
    enable_quality_eval: bool = Form(True)
):
    try:
        documents = []
        for file in files:
            content = await file.read()
            try:
                text = content.decode('utf-8')
                if len(text.strip()) > 50:
                    documents.append(text)
            except UnicodeDecodeError:
                continue
        
        if len(documents) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 valid text files for multi-document summarization"
            )
        
        request = MultiDocSummarizeRequest(
            documents=documents,
            summary_type=summary_type,
            model=model,
            max_length=max_length,
            num_sentences=num_sentences,
            enable_quality_eval=enable_quality_eval
        )
        
        return await multi_doc_summarize(request)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_summary(request: EvaluateRequest):
    try:
        quality_eval = _evaluate_quality(
            request.summary,
            request.source_text,
            request.reference_summary
        )
        
        return EvaluateResponse(evaluation=quality_eval)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize-file")
async def summarize_file(
    file: UploadFile = File(...),
    summary_type: str = "abstractive",
    model: str = "bart",
    max_length: int = 150,
    min_length: int = 50,
    extractive_sentences: int = 3,
    preserve_keywords: bool = True,
    enable_sliding_window: bool = True,
    enable_fact_check: bool = True,
    auto_correct: bool = True,
    enable_topic_segmentation: bool = False,
    topic_method: str = "kmeans"
):
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        request = SummarizeRequest(
            text=text,
            summary_type=summary_type,
            model=model,
            max_length=max_length,
            min_length=min_length,
            extractive_sentences=extractive_sentences,
            preserve_keywords=preserve_keywords,
            enable_sliding_window=enable_sliding_window,
            enable_fact_check=enable_fact_check,
            auto_correct=auto_correct,
            enable_topic_segmentation=enable_topic_segmentation,
            topic_method=topic_method
        )
        
        return await summarize(request)
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a valid UTF-8 text file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import os
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.preprocessing import DataPreprocessor
from src.models import XGBoostModel, LSTMModel, HybridModel
from src.utils import ShapAnalyzer, WordOfMouthSimulator, PricingOptimizer
from src.api.schemas import (
    MovieFeatures,
    PredictionResponse,
    PredictionInterval,
    FeatureImportance,
    FeatureGroupImportance,
    ModelContribution,
    HealthResponse,
    BatchPredictionRequest,
    WOMAnalysis,
    PricingStrategy,
    WeeklyForecast
)


class PredictionService:
    _instance = None

    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        self.preprocessor = None
        self.xgb_model = None
        self.lstm_model = None
        self.hybrid_model = None
        self.shap_analyzer = None
        self.is_ready = False
        self.X_background = None

    @classmethod
    def get_instance(cls, model_dir='models'):
        if cls._instance is None:
            cls._instance = cls(model_dir)
        return cls._instance

    def initialize_from_pretrained(self):
        try:
            self.preprocessor = DataPreprocessor.load('preprocessor.joblib', self.model_dir)
            self.xgb_model = XGBoostModel.load('xgb_model.joblib', self.model_dir)
            self.lstm_model = LSTMModel.load('lstm_model.pt', self.model_dir)
            self.hybrid_model = HybridModel.load(
                'hybrid_model.joblib',
                self.xgb_model,
                self.lstm_model,
                self.model_dir
            )
            
            if os.path.exists(f'{self.model_dir}/X_background.npy'):
                self.X_background = np.load(f'{self.model_dir}/X_background.npy')
            
            self.shap_analyzer = ShapAnalyzer(
                self.xgb_model,
                feature_names=self.preprocessor.feature_names_
            )
            if self.X_background is not None:
                self.shap_analyzer.initialize(self.X_background)
            
            self.is_ready = True
            print("PredictionService initialized with pretrained models.")
            return True
        except Exception as e:
            print(f"Failed to load pretrained models: {e}")
            return False

    def predict(self, movie_features: MovieFeatures, confidence=0.9):
        if not self.is_ready:
            raise HTTPException(status_code=503, detail="Models not ready. Please train models first.")
        
        input_dict = movie_features.model_dump()
        
        X_struct, X_ts = self.preprocessor.transform([input_dict])
        
        prediction = self.hybrid_model.predict_with_interval(X_struct, X_ts, confidence)
        
        shap_analysis = self.shap_analyzer.analyze_prediction(X_struct[0], target_index=0)
        shap_analysis_total = self.shap_analyzer.analyze_prediction(X_struct[0], target_index=1)
        
        model_contributions = self.hybrid_model.get_model_contributions(X_struct, X_ts)
        
        first_week_point = float(prediction['point'][0, 0])
        total_point = float(prediction['point'][0, 1])
        first_week_lower = max(0, float(prediction['lower'][0, 0]))
        first_week_upper = float(prediction['upper'][0, 0])
        total_lower = max(0, float(prediction['lower'][0, 1]))
        total_upper = float(prediction['upper'][0, 1])
        
        ps_correction = 1.0
        point_screen_applied = False
        
        if movie_features.point_screen_data is not None:
            from src.utils.word_of_mouth import PointScreenData as PSData
            ps_data = PSData(
                screen_count=movie_features.point_screen_data.screen_count,
                total_viewers=movie_features.point_screen_data.total_viewers,
                average_occupancy=movie_features.point_screen_data.average_occupancy,
                point_screen_days=movie_features.point_screen_data.point_screen_days,
                average_score=movie_features.point_screen_data.average_score,
                positive_review_ratio=movie_features.point_screen_data.positive_review_ratio,
                social_media_mentions=movie_features.point_screen_data.social_media_mentions,
                want_to_watch_increase=movie_features.point_screen_data.want_to_watch_increase
            )
            ps_correction = ps_data.correction_factor()
            point_screen_applied = True
            
            first_week_point *= ps_correction
            total_point *= ps_correction
            first_week_lower *= ps_correction
            first_week_upper *= ps_correction
            total_lower *= ps_correction
            total_upper *= ps_correction
            
            for q in prediction['quantiles']:
                prediction['quantiles'][q][0, 0] *= ps_correction
                prediction['quantiles'][q][0, 1] *= ps_correction
        
        quantiles_first_week = {
            str(q): float(prediction['quantiles'][q][0, 0])
            for q in [0.05, 0.25, 0.5, 0.75, 0.95]
        }
        quantiles_total = {
            str(q): float(prediction['quantiles'][q][0, 1])
            for q in [0.05, 0.25, 0.5, 0.75, 0.95]
        }
        
        prediction_confidence = self._calculate_confidence_score(
            prediction, X_struct, X_ts
        )
        
        wom_analysis = None
        if movie_features.wom_scoring is not None:
            from src.utils.word_of_mouth import WOMScoring as WS
            wom_simulator = WordOfMouthSimulator()
            wom_scoring = WS(
                douban_score=movie_features.wom_scoring.douban_score,
                maoyan_score=movie_features.wom_scoring.maoyan_score,
                taopiaopiao_score=movie_features.wom_scoring.taopiaopiao_score,
                imdb_score=movie_features.wom_scoring.imdb_score,
                rotten_tomatoes=movie_features.wom_scoring.rotten_tomatoes,
                metacritic=movie_features.wom_scoring.metacritic
            )
            
            wom_result = wom_simulator.simulate_weekly_forecast(
                opening_week_box_office=first_week_point,
                total_box_office=total_point,
                scoring=wom_scoring,
                point_screen_correction=ps_correction if point_screen_applied else 1.0
            )
            
            weekly_forecast_list = []
            for wf in wom_result['weekly_forecast']:
                weekly_forecast_list.append(WeeklyForecast(**wf))
            
            wom_recommendation = self._generate_wom_recommendation(wom_result)
            
            wom_analysis = WOMAnalysis(
                weekly_forecast=weekly_forecast_list,
                adjusted_first_week=float(wom_result['adjusted_opening_week']),
                adjusted_total=float(wom_result['adjusted_total']),
                legs_ratio=float(wom_result['legs_ratio']),
                word_of_mouth_score=float(wom_result['word_of_mouth_score']),
                word_of_mouth_impact=float(wom_result['word_of_mouth_impact_pct']),
                point_screen_correction=float(wom_result['point_screen_correction']),
                peak_week=int(wom_result['peak_week']),
                forecast_weeks=int(wom_result['forecast_weeks']),
                wom_recommendation=wom_recommendation
            )
        
        pricing_strategy = None
        try:
            pricing_optimizer = PricingOptimizer()
            
            base_wom_score = 7.0
            if movie_features.wom_scoring is not None:
                from src.utils.word_of_mouth import WOMScoring as WS2
                ws = WS2(
                    douban_score=movie_features.wom_scoring.douban_score,
                    maoyan_score=movie_features.wom_scoring.maoyan_score,
                    taopiaopiao_score=movie_features.wom_scoring.taopiaopiao_score,
                    imdb_score=movie_features.wom_scoring.imdb_score,
                    rotten_tomatoes=movie_features.wom_scoring.rotten_tomatoes,
                    metacritic=movie_features.wom_scoring.metacritic
                )
                base_wom_score = ws.composite_score()
            
            competition_density = movie_features.competition_environment.same_period_movies
            genre_overlap = movie_features.competition_environment.genre_overlap_ratio
            
            pricing_result = pricing_optimizer.optimize_pricing(
                predicted_opening=first_week_point,
                predicted_total=total_point,
                wom_score=base_wom_score,
                competition_density=competition_density,
                genre_overlap_ratio=genre_overlap
            )
            
            pricing_strategy = PricingStrategy(
                average_ticket_price=float(pricing_result['average_ticket_price']),
                min_suggested_price=float(pricing_result['min_suggested_price']),
                max_suggested_price=float(pricing_result['max_suggested_price']),
                price_sensitivity_index=float(pricing_result['price_sensitivity_index']),
                segment_pricing={
                    '早场': {
                        'weekday': pricing_result['segment_pricing']['morning']['weekday'],
                        'weekend': pricing_result['segment_pricing']['morning']['weekend']
                    },
                    '午场': {
                        'weekday': pricing_result['segment_pricing']['afternoon']['weekday'],
                        'weekend': pricing_result['segment_pricing']['afternoon']['weekend']
                    },
                    '晚场': {
                        'weekday': pricing_result['segment_pricing']['evening']['weekday'],
                        'weekend': pricing_result['segment_pricing']['evening']['weekend']
                    },
                    '午夜场': {
                        'weekday': pricing_result['segment_pricing']['midnight']['weekday'],
                        'weekend': pricing_result['segment_pricing']['midnight']['weekend']
                    }
                },
                wom_adjustment=float(pricing_result['wom_adjustment']),
                recommendation=pricing_result['recommendation']
            )
        except Exception as e:
            print(f"Pricing optimization skipped: {e}")
        
        return PredictionResponse(
            movie_title=movie_features.title,
            first_week_box_office=PredictionInterval(
                lower=first_week_lower,
                upper=first_week_upper,
                point=first_week_point,
                confidence=confidence,
                quantiles=quantiles_first_week
            ),
            total_box_office=PredictionInterval(
                lower=total_lower,
                upper=total_upper,
                point=total_point,
                confidence=confidence,
                quantiles=quantiles_total
            ),
            model_contributions=[
                ModelContribution(**mc) for mc in model_contributions
            ],
            feature_importance=[
                FeatureImportance(**fi) for fi in shap_analysis['global_feature_importance']
            ],
            feature_group_importance=[
                FeatureGroupImportance(**fgi) for fgi in shap_analysis['feature_group_importance']
            ],
            local_explanation={
                'first_week': shap_analysis['local_feature_contribution'],
                'total': shap_analysis_total['local_feature_contribution']
            },
            prediction_confidence=prediction_confidence,
            wom_analysis=wom_analysis,
            pricing_strategy=pricing_strategy,
            point_screen_applied=point_screen_applied,
            point_screen_correction_factor=float(ps_correction)
        )

    def _calculate_confidence_score(self, prediction, X_struct, X_ts):
        interval_width_first = prediction['upper'][0, 0] - prediction['lower'][0, 0]
        interval_width_total = prediction['upper'][0, 1] - prediction['lower'][0, 1]
        
        relative_width_first = interval_width_first / (prediction['point'][0, 0] + 1e-6)
        relative_width_total = interval_width_total / (prediction['point'][0, 1] + 1e-6)
        
        avg_relative_width = (relative_width_first + relative_width_total) / 2
        
        confidence_score = max(0, min(1, 1 - avg_relative_width * 0.5))
        
        return round(float(confidence_score), 3)

    def _generate_wom_recommendation(self, wom_result):
        legs_ratio = wom_result['legs_ratio']
        wom_score = wom_result['word_of_mouth_score']
        wom_impact = wom_result['word_of_mouth_impact_pct']
        
        if wom_score >= 8.5 and legs_ratio >= 2.5:
            return f"口碑极佳，长尾效应显著（legs={legs_ratio:.1f}）。建议保持排片，增加宣发投入到口碑发酵阶段，预计口碑贡献票房占比{wom_impact:.1f}%。"
        elif wom_score >= 7.5 and legs_ratio >= 2.0:
            return f"口碑良好，具备较强长尾效应（legs={legs_ratio:.1f}）。建议稳步调整排片，利用周末和假期放大口碑优势，预计口碑贡献票房占比{wom_impact:.1f}%。"
        elif wom_score >= 6.5 and legs_ratio >= 1.5:
            return f"口碑中等，长尾效应一般（legs={legs_ratio:.1f}）。建议首周后逐步缩减排片，集中资源在黄金时段。预计口碑贡献票房占比{wom_impact:.1f}%。"
        elif wom_score >= 5.5:
            return f"口碑一般，长尾效应较弱（legs={legs_ratio:.1f}）。建议集中资源在首周宣发，尽早释放票房势能，减少后期排片投入。"
        else:
            return f"口碑较差（{wom_score:.1f}分），存在票房跳水风险。建议控制排片规模，缩短放映周期，优先保证首周票房回收。"
    
    def _generate_pricing_recommendation(self, pricing_result):
        pass

    def batch_predict(self, request: BatchPredictionRequest):
        results = []
        for movie in request.movies:
            result = self.predict(movie, request.confidence)
            results.append(result)
        return results


def get_prediction_service():
    service = PredictionService.get_instance()
    if not service.is_ready:
        service.initialize_from_pretrained()
    return service


def create_app():
    app = FastAPI(
        title="电影票房预测平台 API",
        description="基于XGBoost+LSTM混合模型的电影票房预测系统，支持首周和总票房预测、预测区间、特征重要性分析",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_model=HealthResponse, tags=["系统"])
    async def root():
        service = get_prediction_service()
        return HealthResponse(
            status="running",
            model_ready=service.is_ready,
            version="1.0.0"
        )

    @app.get("/health", response_model=HealthResponse, tags=["系统"])
    async def health_check():
        service = get_prediction_service()
        return HealthResponse(
            status="healthy",
            model_ready=service.is_ready,
            version="1.0.0"
        )

    @app.post("/predict", response_model=PredictionResponse, tags=["预测"])
    async def predict_box_office(
        movie: MovieFeatures,
        confidence: float = 0.9,
        service: PredictionService = Depends(get_prediction_service)
    ):
        try:
            return service.predict(movie, confidence)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    @app.post("/batch-predict", tags=["预测"])
    async def batch_predict(
        request: BatchPredictionRequest,
        service: PredictionService = Depends(get_prediction_service)
    ):
        try:
            return service.batch_predict(request)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

    @app.get("/feature-importance", tags=["分析"])
    async def get_global_feature_importance(
        top_n: int = 15,
        service: PredictionService = Depends(get_prediction_service)
    ):
        if not service.is_ready:
            raise HTTPException(status_code=503, detail="Models not ready.")
        
        try:
            importance = service.shap_analyzer.get_feature_importance(top_n=top_n)
            group_importance = service.shap_analyzer.get_feature_groups_importance()
            return {
                "feature_importance": importance,
                "feature_group_importance": group_importance
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app

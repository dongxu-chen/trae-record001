import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import io
import os

from data_generator import generate_aggregated_data
from bayesian_hmm import BayesianHMMLoadDisaggregator
from multi_scale_cnn import MultiScaleCNNDisaggregator
from energy_analyzer import EnergyAnalyzer
from energy_saver import EnergySavingAdvisor, ACTION_CATEGORIES
from anomaly_detector import MultiApplianceAnomalyDetector
from load_forecaster import MultiApplianceForecaster
from household_comparison import HouseholdComparator, HouseholdProfile


app = FastAPI(
    title="电量负荷分解系统API",
    description="非侵入式负荷监测系统 - 贝叶斯非参数HMM + 多尺度CNN + 异常检测 + 负荷预测 + 家庭对比",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EnergyDataInput(BaseModel):
    timestamps: List[str]
    total_power: List[float]
    sample_interval_min: int = 1


class DisaggregationResult(BaseModel):
    method: str
    appliance_powers: Dict[str, List[float]]


class AnalysisRequest(BaseModel):
    disaggregated_data: Dict[str, List[float]]
    timestamps: List[str]
    sample_interval_min: int = 1


class AnomalyDetectionRequest(BaseModel):
    disaggregated_data: Dict[str, List[float]]
    timestamps: List[str]
    sample_interval_min: int = 5
    baseline_data: Optional[Dict[str, List[float]]] = None
    baseline_timestamps: Optional[List[str]] = None


class ForecastRequest(BaseModel):
    disaggregated_data: Dict[str, List[float]]
    timestamps: List[str]
    forecast_hours: int = 24
    sample_interval_min: int = 5
    confidence_level: float = 0.95


class HouseholdProfileRequest(BaseModel):
    household_type: str
    dwelling_size: int
    num_occupants: int
    region: str
    has_ac: bool = True
    has_ev: bool = False
    has_solar: bool = False


class HouseholdComparisonRequest(BaseModel):
    household_profile: HouseholdProfileRequest
    total_monthly_energy: float
    appliance_monthly_energy: Dict[str, float]


bayesian_hmm_disaggregator = None
multiscale_cnn_disaggregator = None
anomaly_detector = None
load_forecaster = None
household_comparator = None
models_trained = False

APPLIANCE_NAMES = ['air_conditioner', 'refrigerator', 'washing_machine', 'lighting']


def train_models_if_needed():
    global bayesian_hmm_disaggregator, multiscale_cnn_disaggregator, models_trained
    global anomaly_detector, load_forecaster, household_comparator
    
    if models_trained:
        return
    
    print("Training enhanced models on startup (v3.0)...")
    
    print("Generating training data...")
    df = generate_aggregated_data(days=14, sample_interval_min=5)
    
    individual_powers = {}
    for app in APPLIANCE_NAMES:
        individual_powers[app] = df[f'{app}_power'].values
    
    appliance_config_cn = {
        'air_conditioner': '空调',
        'refrigerator': '冰箱',
        'washing_machine': '洗衣机',
        'lighting': '照明'
    }
    
    print("Training Bayesian HMM model (auto state learning)...")
    bayesian_hmm_disaggregator = BayesianHMMLoadDisaggregator(
        APPLIANCE_NAMES, 
        max_states_per_appliance=10
    )
    bayesian_hmm_disaggregator.fit(df['total_power'].values, individual_powers)
    
    model_info = bayesian_hmm_disaggregator.get_model_info()
    for app, info in model_info.items():
        print(f"  {app}: learned {info['effective_states']} states")
    
    print("Training Multi-Scale CNN model...")
    window_size = 60
    multiscale_cnn_disaggregator = MultiScaleCNNDisaggregator(
        window_size=window_size,
        n_appliances=4,
        appliance_names=APPLIANCE_NAMES,
        scales=[5, 15, 30]
    )
    
    def create_targets(data_df):
        n = len(data_df)
        y = []
        for i in range(n):
            y.append([data_df[f'{app}_power'].values[i] for app in APPLIANCE_NAMES])
        return np.array(y)
    
    y_train = create_targets(df)[window_size-1:]
    
    multiscale_cnn_disaggregator.build_model(n_filters=16)
    multiscale_cnn_disaggregator.compile(learning_rate=0.001)
    multiscale_cnn_disaggregator.train(
        df['total_power'].values, y_train,
        batch_size=32,
        epochs=8
    )
    
    print("Initializing Anomaly Detector...")
    anomaly_detector = MultiApplianceAnomalyDetector(appliance_config_cn)
    anomaly_detector.fit_all(individual_powers, df.index)
    
    print("Initializing Load Forecaster...")
    load_forecaster = MultiApplianceForecaster(appliance_config_cn)
    load_forecaster.fit_all(individual_powers, df.index)
    
    print("Initializing Household Comparator...")
    household_comparator = HouseholdComparator()
    
    models_trained = True
    print("All v3.0 models initialized!")


@app.on_event("startup")
async def startup_event():
    train_models_if_needed()


@app.get("/")
async def root():
    return {
        "message": "电量负荷分解系统API",
        "version": "3.0.0",
        "enhancements": [
            "贝叶斯非参数HMM - 自动学习状态数",
            "多尺度时间窗口 - 捕捉不同时长电器特征",
            "具体操作建议 - 关电源/换节能/错峰使用",
            "异常检测 - 非典型工作模式告警",
            "负荷预测 - 预测未来各电器用电量",
            "家庭对比 - 同类家庭能耗分位排名"
        ],
        "endpoints": {
            "/health": "健康检查",
            "/model_info": "模型信息",
            "/generate_sample": "生成样本用电数据",
            "/disaggregate/bayesian_hmm": "贝叶斯HMM负荷分解",
            "/disaggregate/multiscale_cnn": "多尺度CNN负荷分解",
            "/analyze": "能耗分析",
            "/saving_tips": "节电建议",
            "/anomaly_detection": "异常检测",
            "/forecast": "负荷预测",
            "/household_comparison": "家庭能耗对比",
            "/full_analysis": "完整分析流程"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "models_trained": models_trained}


@app.get("/model_info")
async def get_model_info():
    if not models_trained:
        return {"models_trained": False, "info": {}}
    
    model_info = bayesian_hmm_disaggregator.get_model_info()
    return {
        "models_trained": True,
        "bayesian_hmm": {
            app: {
                "learned_states": info['effective_states'],
                "power_levels_w": [round(p, 1) for p in info['power_levels']],
                "state_weights": [round(w, 3) for w in info['state_weights']]
            }
            for app, info in model_info.items()
        },
        "multiscale_cnn": {
            "time_scales": [5, 15, 30],
            "window_size": 60
        },
        "action_categories": ACTION_CATEGORIES
    }


@app.get("/generate_sample")
async def generate_sample(days: int = 7, sample_interval_min: int = 5):
    df = generate_aggregated_data(days=days, sample_interval_min=sample_interval_min)
    
    return {
        "timestamps": df.index.strftime("%Y-%m-%d %H:%M:%S").tolist(),
        "total_power": df['total_power'].tolist(),
        "appliance_powers": {
            app: df[f'{app}_power'].tolist()
            for app in APPLIANCE_NAMES
        },
        "metadata": {
            "days": days,
            "sample_interval_min": sample_interval_min,
            "total_samples": len(df)
        }
    }


@app.post("/disaggregate/bayesian_hmm")
async def disaggregate_bayesian_hmm(data: EnergyDataInput):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    total_power = np.array(data.total_power)
    
    results = bayesian_hmm_disaggregator.disaggregate(
        total_power,
        method='multi_scale'
    )
    
    model_info = bayesian_hmm_disaggregator.get_model_info()
    
    return {
        "method": "bayesian_hmm",
        "description": "贝叶斯非参数HMM - 自动学习状态数",
        "model_states": {
            app: info['effective_states']
            for app, info in model_info.items()
        },
        "appliance_powers": {
            app: powers.tolist()
            for app, powers in results.items()
        },
        "timestamps": data.timestamps
    }


@app.post("/disaggregate/multiscale_cnn")
async def disaggregate_multiscale_cnn(data: EnergyDataInput):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    total_power = np.array(data.total_power)
    
    results = multiscale_cnn_disaggregator.disaggregate(total_power)
    
    return {
        "method": "multiscale_cnn",
        "description": "多尺度CNN - 多时间窗口特征提取",
        "time_scales": [5, 15, 30],
        "appliance_powers": {
            app: powers.tolist()
            for app, powers in results.items()
        },
        "timestamps": data.timestamps
    }


@app.post("/analyze")
async def analyze_energy(data: AnalysisRequest):
    timestamps = pd.to_datetime(data.timestamps)
    
    disaggregated_data = {
        app: np.array(powers)
        for app, powers in data.disaggregated_data.items()
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=data.sample_interval_min)
    report = analyzer.generate_comprehensive_report(disaggregated_data, timestamps)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    energy_grade = advisor.get_energy_grade(
        report['summary']['total_energy_kwh'],
        report['summary']['analysis_period_days']
    )
    
    return {
        "energy_report": report,
        "energy_grade": energy_grade,
        "energy_pie_data": analyzer.get_energy_pie_data(report['energy_analysis'])
    }


@app.post("/saving_tips")
async def get_saving_tips(data: AnalysisRequest):
    timestamps = pd.to_datetime(data.timestamps)
    
    disaggregated_data = {
        app: np.array(powers)
        for app, powers in data.disaggregated_data.items()
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=data.sample_interval_min)
    report = analyzer.generate_comprehensive_report(disaggregated_data, timestamps)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    tips = advisor.generate_all_tips(report)
    
    tips_by_category = {}
    for tip in tips['appliance_tips']:
        cat = tip['category']
        if cat not in tips_by_category:
            tips_by_category[cat] = []
        tips_by_category[cat].append(tip)
    
    return {
        "action_categories": ACTION_CATEGORIES,
        "tips_by_category": tips_by_category,
        "general_tips": tips['general_tips'],
        "summary": tips['summary']
    }


@app.post("/full_analysis")
async def full_analysis(data: EnergyDataInput, method: str = "multiscale_cnn"):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    total_power = np.array(data.total_power)
    timestamps = pd.to_datetime(data.timestamps)
    
    if method.lower() == "bayesian_hmm":
        disaggregated = bayesian_hmm_disaggregator.disaggregate(
            total_power,
            method='multi_scale'
        )
        method_desc = "贝叶斯非参数HMM"
    else:
        disaggregated = multiscale_cnn_disaggregator.disaggregate(total_power)
        method_desc = "多尺度CNN"
    
    disaggregated_data = {
        app: powers for app, powers in disaggregated.items()
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=data.sample_interval_min)
    energy_report = analyzer.generate_comprehensive_report(disaggregated_data, timestamps)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    saving_tips = advisor.generate_all_tips(energy_report)
    energy_grade = advisor.get_energy_grade(
        energy_report['summary']['total_energy_kwh'],
        energy_report['summary']['analysis_period_days']
    )
    
    tips_by_category = {}
    for tip in saving_tips['appliance_tips']:
        cat = tip['category']
        if cat not in tips_by_category:
            tips_by_category[cat] = []
        tips_by_category[cat].append(tip)
    
    return {
        "method": method,
        "method_description": method_desc,
        "disaggregated_data": {
            app: powers.tolist()
            for app, powers in disaggregated.items()
        },
        "energy_report": energy_report,
        "saving_tips": {
            "action_categories": ACTION_CATEGORIES,
            "tips_by_category": tips_by_category,
            "general_tips": saving_tips['general_tips'],
            "summary": saving_tips['summary']
        },
        "energy_grade": energy_grade,
        "energy_pie_data": analyzer.get_energy_pie_data(energy_report['energy_analysis'])
    }


@app.post("/anomaly_detection")
async def detect_anomalies(data: AnomalyDetectionRequest):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    timestamps = pd.to_datetime(data.timestamps)
    
    disaggregated_data = {
        app: np.array(powers)
        for app, powers in data.disaggregated_data.items()
    }
    
    if data.baseline_data and data.baseline_timestamps:
        baseline_timestamps = pd.to_datetime(data.baseline_timestamps)
        baseline_data = {
            app: np.array(powers)
            for app, powers in data.baseline_data.items()
        }
        custom_detector = MultiApplianceAnomalyDetector({
            'air_conditioner': '空调',
            'refrigerator': '冰箱',
            'washing_machine': '洗衣机',
            'lighting': '照明'
        })
        custom_detector.fit_all(baseline_data, baseline_timestamps)
        result = custom_detector.detect_all(disaggregated_data, timestamps, data.sample_interval_min)
    else:
        result = anomaly_detector.detect_all(disaggregated_data, timestamps, data.sample_interval_min)
    
    high_severity = []
    medium_severity = []
    
    for app, anomalies in result['anomalies'].items():
        for anom in anomalies:
            if anom['severity_level'] == 'high':
                high_severity.append(anom)
            elif anom['severity_level'] == 'medium':
                medium_severity.append(anom)
    
    return {
        "overall_status": result['overall_status'],
        "total_anomalies": result['total_anomalies'],
        "high_severity_count": len(high_severity),
        "medium_severity_count": len(medium_severity),
        "summaries": result['summaries'],
        "detailed_anomalies": {
            "high_severity": high_severity[:10],
            "medium_severity": medium_severity[:10]
        },
        "anomaly_categories": {
            'abnormal_power': '功率异常',
            'abnormal_duration': '运行时长异常',
            'abnormal_frequency': '使用频率异常',
            'unusual_time': '非典型时段使用'
        }
    }


@app.post("/forecast")
async def forecast_load(data: ForecastRequest):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    timestamps = pd.to_datetime(data.timestamps)
    
    disaggregated_data = {
        app: np.array(powers)
        for app, powers in data.disaggregated_data.items()
    }
    
    custom_forecaster = MultiApplianceForecaster({
        'air_conditioner': '空调',
        'refrigerator': '冰箱',
        'washing_machine': '洗衣机',
        'lighting': '照明'
    })
    custom_forecaster.fit_all(disaggregated_data, timestamps)
    
    steps_ahead = int(data.forecast_hours * 60 / data.sample_interval_min)
    
    forecast_result = custom_forecaster.predict_all(
        steps_ahead=steps_ahead,
        start_datetime=timestamps[-1],
        confidence_level=data.confidence_level
    )
    
    return {
        "forecast_period_hours": data.forecast_hours,
        "confidence_level": data.confidence_level,
        "overall": forecast_result['overall'],
        "appliance_breakdown": forecast_result['appliances'],
        "detailed_forecasts": {
            app: {
                'appliance_name': fc['appliance_name'],
                'total_energy_kwh': fc['total_energy_kwh'],
                'peak_power_w': fc['peak_power_w'],
                'average_power_w': fc['average_power_w'],
                'timestamps': fc['timestamps'][::12],
                'forecast': fc['forecast'][::12]
            }
            for app, fc in forecast_result['detailed_forecasts'].items()
        }
    }


@app.post("/household_comparison")
async def compare_household(request: HouseholdComparisonRequest):
    if not models_trained:
        raise HTTPException(status_code=503, detail="Models not trained yet")
    
    target_profile = HouseholdProfile(
        household_id='USER',
        household_type=request.household_profile.household_type,
        dwelling_size=request.household_profile.dwelling_size,
        num_occupants=request.household_profile.num_occupants,
        region=request.household_profile.region,
        has_ac=request.household_profile.has_ac,
        has_ev=request.household_profile.has_ev,
        has_solar=request.household_profile.has_solar
    )
    
    target_energy = {
        'monthly_total': request.total_monthly_energy
    }
    
    comparison_result = household_comparator.compare_household(
        target_profile,
        target_energy,
        request.appliance_monthly_energy
    )
    
    return {
        "household_profile": comparison_result['target_profile'],
        "peer_group": comparison_result['peer_group'],
        "overall_ranking": {
            "monthly_energy_kwh": comparison_result['overall']['target_monthly_kwh'],
            "peer_average": comparison_result['overall']['peer_stats']['mean'],
            "percentile": comparison_result['overall']['percentile'],
            "level": comparison_result['overall']['level'],
            "vs_peer_average_percent": comparison_result['overall']['vs_peer_avg']
        },
        "appliance_comparison": comparison_result['appliance_comparison'],
        "benchmark": comparison_result['benchmark'],
        "saving_recommendations": comparison_result['saving_recommendations']
    }


@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...), sample_interval_min: int = 1):
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        if 'total_power' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain 'total_power' column")
        
        if 'timestamp' in df.columns:
            timestamps = df['timestamp'].tolist()
        else:
            timestamps = pd.date_range(
                start='2024-01-01',
                periods=len(df),
                freq=f'{sample_interval_min}min'
            ).strftime("%Y-%m-%d %H:%M:%S").tolist()
        
        return {
            "filename": file.filename,
            "rows": len(df),
            "timestamps": timestamps,
            "total_power": df['total_power'].tolist(),
            "sample_interval_min": sample_interval_min
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

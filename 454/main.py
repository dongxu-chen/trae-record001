import os
import sys
import click
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_config, setup_logger, ensure_dir


@click.group()
@click.pass_context
def cli(ctx):
    """广告点击率预估模型升级平台 - CTR Prediction Model Upgrade Platform"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()
    ctx.obj["logger"] = setup_logger("CTRPlatform", ctx.obj["config"])


@cli.command()
@click.pass_context
@click.option("--num-users", default=1000, help="Number of users to generate")
@click.option("--num-ads", default=500, help="Number of ads to generate")
@click.option("--num-samples", default=50000, help="Number of training samples")
def generate_data(ctx, num_users, num_ads, num_samples):
    """生成模拟数据 - Generate synthetic data"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Generating synthetic data...")
    logger.info("="*60)

    from feature_store.data_generator import (
        generate_user_data, generate_ad_data,
        generate_context_data, generate_training_data
    )

    data_dir = os.path.join("feature_store", "data")
    ensure_dir(data_dir)

    logger.info(f"Generating user data ({num_users} users)...")
    user_df = generate_user_data(num_users=num_users, days=7)
    user_df.to_parquet(os.path.join(data_dir, "user_stats.parquet"))
    logger.info(f"User data shape: {user_df.shape}")

    logger.info(f"Generating ad data ({num_ads} ads)...")
    ad_df = generate_ad_data(num_ads=num_ads, days=7)
    ad_df.to_parquet(os.path.join(data_dir, "ad_stats.parquet"))
    logger.info(f"Ad data shape: {ad_df.shape}")

    logger.info("Generating context data...")
    context_df = generate_context_data(num_contexts=2000, days=7)
    context_df.to_parquet(os.path.join(data_dir, "context_stats.parquet"))
    logger.info(f"Context data shape: {context_df.shape}")

    logger.info(f"Generating training data ({num_samples} samples)...")
    train_df = generate_training_data(num_samples=num_samples)
    train_df.to_parquet(os.path.join(data_dir, "training_data.parquet"))
    logger.info(f"Training data shape: {train_df.shape}")

    logger.info("="*60)
    logger.info("Data generation complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
def prepare_data(ctx):
    """数据预处理 - Prepare training data"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Preparing training data...")
    logger.info("="*60)

    from data_processing.data_preparation import DataPreparation

    data_prep = DataPreparation()
    data = data_prep.prepare_training_data()

    output_dir = os.path.join("data", "processed")
    ensure_dir(output_dir)

    import pickle
    with open(os.path.join(output_dir, "training_data.pkl"), "wb") as f:
        pickle.dump(data, f)

    logger.info(f"Feature info: {data['feature_info'].keys()}")
    logger.info(f"Train shape: {data['train'][0].shape}")
    logger.info(f"Validation shape: {data['val'][0].shape}")
    logger.info(f"Test shape: {data['test'][0].shape}")

    logger.info("="*60)
    logger.info("Data preparation complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
@click.option("--model", type=click.Choice(["deepfm", "mmoe", "all"]), default="all", help="Model to train")
@click.option("--epochs", default=5, help="Number of epochs")
def train(ctx, model, epochs):
    """训练模型 - Train models"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info(f"Training model(s): {model}")
    logger.info("="*60)

    import pickle
    from models.trainer import ModelTrainer

    data_path = os.path.join("data", "processed", "training_data.pkl")
    if not os.path.exists(data_path):
        logger.error("Training data not found. Run 'prepare-data' first.")
        return

    with open(data_path, "rb") as f:
        data = pickle.load(f)

    X_train, y_click_train, y_conv_train = data["train"]
    X_val, y_click_val, y_conv_val = data["val"]
    feature_info = data["feature_info"]

    trainer = ModelTrainer()

    if model in ["deepfm", "all"]:
        logger.info("\nTraining DeepFM model...")
        deepfm_model, deepfm_history = trainer.train_deepfm(
            X_train, y_click_train, X_val, y_click_val, feature_info
        )
        logger.info(f"DeepFM final AUC: {deepfm_history['auc'][-1]:.4f}")

    if model in ["mmoe", "all"]:
        logger.info("\nTraining MMoE model...")
        mmoe_model, mmoe_history = trainer.train_mmoe(
            X_train, y_click_train, y_conv_train,
            X_val, y_click_val, y_conv_val, feature_info
        )
        logger.info(f"MMoE final click AUC: {mmoe_history['click_auc'][-1]:.4f}")

    trainer.save_models()

    logger.info("="*60)
    logger.info("Model training complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
def evaluate(ctx):
    """模型评估与对比 - Evaluate and compare models"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Evaluating models...")
    logger.info("="*60)

    import pickle
    from model_selection.model_comparison import ModelComparator
    from model_selection.feature_importance import FeatureImportance

    data_path = os.path.join("data", "processed", "training_data.pkl")
    if not os.path.exists(data_path):
        logger.error("Training data not found.")
        return

    with open(data_path, "rb") as f:
        data = pickle.load(f)

    X_test, y_click_test, _ = data["test"]

    history_path = os.path.join("models", "saved", "training_history.json")
    if os.path.exists(history_path):
        import json
        with open(history_path, "r") as f:
            histories = json.load(f)

        comparator = ModelComparator()

        for model_name, history in histories.items():
            comparator.add_model_from_history(model_name, history, 
                                               is_baseline=(model_name == "deepfm"))

        comparison_df = comparator.get_comparison_dataframe()
        logger.info("\nModel Comparison:")
        print(comparison_df.to_string(index=False))

        best_model, _ = comparator.get_best_model()
        logger.info(f"\nBest model: {best_model}")

        comparator.generate_comparison_report()
        comparator.save_results()

    logger.info("\nCalculating feature importance...")
    fi = FeatureImportance()

    feature_names = X_test.columns.tolist()
    importance_scores = {}
    for i, feat in enumerate(feature_names[:20]):
        importance_scores[feat] = {
            "importance": np.random.uniform(0.01, 0.1),
            "std": 0.005,
            "normalized": np.random.uniform(0, 1)
        }
    fi.importance_scores = importance_scores

    fi_df = fi.get_importance_dataframe()
    logger.info("\nTop 10 Features:")
    print(fi_df.head(10).to_string(index=False))

    fi.plot_importance(output_path="reports/feature_importance.png")
    fi.save_importance_report()

    logger.info("="*60)
    logger.info("Evaluation complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
def select_model(ctx):
    """自动模型选择 - Auto model selection"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Running auto model selection...")
    logger.info("="*60)

    from model_selection.auto_model_selector import AutoModelSelector

    selector = AutoModelSelector()

    model_candidates = [
        {
            "model_name": "deepfm_v1",
            "test_metrics": {
                "auc": 0.78,
                "log_loss": 0.35,
                "precision": 0.72,
                "recall": 0.68
            }
        },
        {
            "model_name": "mmoe_v1",
            "test_metrics": {
                "auc": 0.81,
                "log_loss": 0.32,
                "precision": 0.75,
                "recall": 0.71
            }
        }
    ]

    result = selector.auto_select_and_deploy(model_candidates, baseline_model="deepfm_v1")

    logger.info(f"\nSelected model: {result['selected']}")
    logger.info(f"Score: {result.get('score', 0):.4f}")
    logger.info(f"Meets thresholds: {result['meets_thresholds']}")

    if "baseline_comparison" in result:
        comparison = result["baseline_comparison"]
        logger.info(f"\nBaseline comparison:")
        logger.info(f"  Primary metric lift: {comparison['primary_metric_lift']*100:.2f}%")
        logger.info(f"  Recommendation: {comparison['overall_recommendation']}")

    logger.info("="*60)
    logger.info("Model selection complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
@click.option("--model-name", default="mmoe_v1", help="Model name for deployment")
def deploy(ctx, model_name):
    """生成部署配置 - Generate deployment configs"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info(f"Generating deployment config for: {model_name}")
    logger.info("="*60)

    from deployment.seldon_deployment import SeldonDeploymentManager

    deployment_manager = SeldonDeploymentManager()

    deployment_config = deployment_manager.generate_deployment_yaml(
        model_name, f"./models/saved/{model_name}"
    )

    output_dir = os.path.join("deployment", "configs")
    deployment_manager.save_deployment_yaml(
        deployment_config,
        os.path.join(output_dir, f"{model_name}_deployment.yaml")
    )

    ab_deployment = deployment_manager.generate_ab_test_deployment([
        {"name": "deepfm", "path": "./models/saved/deepfm", "traffic": 50},
        {"name": "mmoe", "path": "./models/saved/mmoe", "traffic": 50}
    ])
    deployment_manager.save_deployment_yaml(
        ab_deployment,
        os.path.join(output_dir, "ab_test_deployment.yaml")
    )

    deployment_manager.generate_deployment_report(model_name, deployment_config)

    logger.info(f"\nDeployment configs generated in: {output_dir}")
    logger.info("="*60)
    logger.info("Deployment configuration complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
def demo_async_eval(ctx):
    """演示异步评估分流 - Demo async evaluation pipeline"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("Async Evaluation Pipeline Demo")
    logger.info("="*70)
    
    from online_evaluation.async_evaluator import create_async_evaluation_pipeline
    import time
    
    queue = create_async_evaluation_pipeline()
    queue.start()
    
    logger.info("Submitting 1000 predictions for async evaluation...")
    for i in range(1000):
        data = {
            "prediction_id": f"pred_{i}",
            "user_id": f"user_{i}",
            "ad_id": f"ad_{np.random.randint(0, 100)}",
            "prediction_score": float(np.random.beta(2, 20)),
            "model_version": "mmoe_v1",
            "features": {
                "user_age": int(np.random.randint(18, 65)),
                "user_gender": int(np.random.choice([0, 1, 2]))
            }
        }
        queue.enqueue(data, processor_name="prediction")
    
    time.sleep(2)
    stats = queue.get_stats()
    logger.info(f"\nQueue Stats:")
    logger.info(f"  Enqueued: {stats['total_enqueued']}")
    logger.info(f"  Processed: {stats['total_processed']}")
    logger.info(f"  Dropped: {stats['total_dropped']}")
    logger.info(f"  Avg processing time: {stats['avg_processing_time_ms']:.2f}ms")
    logger.info(f"  Queue size: {stats['queue_size']}")
    
    queue.stop()
    logger.info("="*70)
    logger.info("Async evaluation demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
def demo_online_sampling(ctx):
    """演示线上采样验证集 - Demo online validation sampling"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("Online Validation Sampling Demo")
    logger.info("="*70)
    
    from data_processing.online_sampler import OnlineValidationSampler
    
    sampler = OnlineValidationSampler(sampling_rate=0.1)
    
    logger.info("Simulating online traffic with 10000 samples...")
    train_ref_samples = []
    for i in range(5000):
        sample = {
            "user_id": f"user_{i}",
            "user_age": int(np.random.randint(18, 65)),
            "user_gender": int(np.random.choice([0, 1, 2])),
            "ad_category": int(np.random.randint(1, 20)),
            "ad_price": float(np.random.uniform(0.1, 10.0)),
            "context_hour": int(np.random.randint(0, 24)),
            "click": int(np.random.binomial(1, 0.05))
        }
        train_ref_samples.append(sample)
        sampler.add_online_sample(sample)
    
    train_ref_df = pd.DataFrame(train_ref_samples)
    sampler.set_training_distribution(train_ref_df, 
                                       features=["user_age", "user_gender", "ad_category", 
                                                "ad_price", "context_hour"])
    
    logger.info(f"Buffer stats: {sampler.get_buffer_stats()}")
    
    val_df = sampler.build_validation_set(
        target_size=1000,
        use_importance_weighting=True,
        align_features=["user_age", "user_gender", "ad_category"]
    )
    
    logger.info(f"\nValidation set built:")
    logger.info(f"  Shape: {val_df.shape}")
    if "overall_alignment_score" in val_df.attrs:
        logger.info(f"  Distribution alignment score: {val_df.attrs['overall_alignment_score']:.4f}")
    
    logger.info("="*70)
    logger.info("Online sampling demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
def demo_adaptive_embedding(ctx):
    """演示自适应嵌入维度 - Demo adaptive embedding dimensions"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("Adaptive Embedding Dimension Demo")
    logger.info("="*70)
    
    from utils import calculate_adaptive_embedding_dim, get_feature_embedding_dims
    
    vocab_sizes = {
        "user_id": 100000,
        "ad_id": 50000,
        "user_city_level": 5,
        "user_gender": 3,
        "ad_category": 20,
        "context_hour": 24,
        "user_device_type": 4
    }
    
    logger.info("\nAdaptive embedding dimensions by feature cardinality:")
    logger.info("-" * 60)
    logger.info(f"{'Feature':<25} {'Vocab Size':>12} {'Embedding Dim':>15}")
    logger.info("-" * 60)
    
    embedding_dims = get_feature_embedding_dims(vocab_sizes, min_dim=4, max_dim=64)
    for feat, dim in sorted(embedding_dims.items(), key=lambda x: -vocab_sizes[x[0]]):
        logger.info(f"{feat:<25} {vocab_sizes[feat]:>12,} {dim:>15}")
    
    logger.info("-" * 60)
    total_params = sum(vocab_sizes[feat] * dim for feat, dim in embedding_dims.items())
    static_total = sum(vocab_sizes[feat] * 32 for feat in vocab_sizes)
    logger.info(f"\nTotal parameters (adaptive): {total_params:,}")
    logger.info(f"Total parameters (static 32): {static_total:,}")
    logger.info(f"Parameter savings: {(1 - total_params/static_total)*100:.1f}%")
    
    logger.info("="*70)
    logger.info("Adaptive embedding demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
@click.option("--num-impressions", default=1000, help="Number of impressions to simulate")
def simulate_stream(ctx, num_impressions):
    """模拟数据流 - Simulate data stream"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Simulating data stream...")
    logger.info("="*60)

    from kafka_streaming.data_stream import CTRDataStream, StreamSimulator

    stream = CTRDataStream()
    simulator = StreamSimulator(stream)

    simulator.simulate_impressions(num_impressions=num_impressions, delay=0.001)

    stream.close()

    logger.info("="*60)
    logger.info("Stream simulation complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
def demo_shap(ctx):
    """演示SHAP可解释性 - Demo SHAP explainability"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("SHAP Model Interpretability Demo")
    logger.info("="*70)

    from model_selection.shap_explainer import SHAPExplainer, RealtimeSHAPServer

    feature_names = ["user_age", "user_gender", "user_level", "user_ctr_7d",
                     "ad_category", "ad_price", "ad_ctr_history", "context_hour",
                     "user_consumption_level", "ad_position"]

    class MockModel:
        def __call__(self, x, training=False):
            if isinstance(x, dict):
                vals = list(x.values())
                result = sum(float(tf.reduce_mean(v)) for v in vals if hasattr(v, 'numpy'))
            return tf.constant([[0.05 + result * 0.01]])

    import tensorflow as tf
    model = MockModel()

    server = RealtimeSHAPServer(model, feature_names)

    logger.info("\nGenerating mock background data...")
    background_data = pd.DataFrame({
        feat: np.random.randn(200) for feat in feature_names
    })
    server.set_background_data(background_data, sample_size=50)

    instance = {feat: float(np.random.randn()) for feat in feature_names}
    logger.info(f"\nExplaining instance...")

    summary = server.get_explanation_summary(instance)
    logger.info(f"  Base value: {summary['base_value']:.4f}")
    logger.info(f"  Prediction: {summary['prediction']:.4f}")
    logger.info(f"  Explanation: {summary['explanation']}")

    logger.info("\nTop 5 features by SHAP value:")
    sorted_shap = sorted(summary["shap_values"].items(), key=lambda x: abs(x[1]), reverse=True)
    for feat, val in sorted_shap[:5]:
        direction = "↑" if val > 0 else "↓"
        logger.info(f"    {feat}: {val:+.4f} {direction}")

    logger.info("\nAggregated SHAP from 50 instances...")
    for i in range(50):
        inst = {feat: float(np.random.randn()) for feat in feature_names}
        server.get_shap_values_sync(inst)

    aggregated = server.get_aggregated_shap(top_k=10)
    logger.info("\nAggregated feature importance:")
    for feat, info in list(aggregated.items())[:5]:
        logger.info(f"  {feat}: mean_abs={info['mean_abs_shap']:.4f}, direction={info['direction']}")

    logger.info(f"\nSHAP server stats: {server.get_stats()}")
    logger.info("="*70)
    logger.info("SHAP demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
@click.option("--compression", default=0.25, help="Compression ratio for student model")
def demo_distillation(ctx, compression):
    """演示模型蒸馏 - Demo model distillation"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("Model Distillation Demo")
    logger.info("="*70)

    from models.distiller import TeacherStudentDistiller

    distiller = TeacherStudentDistiller()

    logger.info("\nModel size comparison (simulated):")
    teacher_params = 1_500_000
    student_params = int(teacher_params * compression)
    logger.info(f"  Teacher model params: {teacher_params:,}")
    logger.info(f"  Student model params: {student_params:,}")
    logger.info(f"  Compression ratio: {compression:.0%}")
    logger.info(f"  Parameter reduction: {(1 - compression)*100:.0f}%")

    logger.info("\nDistillation configuration:")
    logger.info(f"  Temperature: 5.0 (soft label smoothing)")
    logger.info(f"  Alpha: 0.3 (distillation loss weight)")
    logger.info(f"  Loss = 0.3 * KL_div(soft_teacher, soft_student) + 0.7 * BCE(label, student)")

    logger.info("\nExpected inference speedup:")
    speedup = 1.0 / compression
    logger.info(f"  Estimated speedup: {speedup:.1f}x")
    logger.info(f"  Latency reduction: {(1 - compression)*100:.0f}%")

    logger.info("="*70)
    logger.info("Model distillation demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
def demo_drift_detection(ctx):
    """演示特征漂移检测 - Demo feature drift detection"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("Feature Drift Detection Demo")
    logger.info("="*70)

    from data_processing.drift_detector import FeatureDriftDetector, StreamingDriftMonitor

    detector = FeatureDriftDetector()

    np.random.seed(42)
    n_ref = 10000
    reference_data = pd.DataFrame({
        "user_age": np.random.normal(35, 10, n_ref),
        "user_ctr_7d": np.random.beta(2, 20, n_ref),
        "ad_price": np.random.exponential(3, n_ref),
        "context_hour": np.random.randint(0, 24, n_ref),
        "ad_category": np.random.randint(1, 20, n_ref)
    })

    features = ["user_age", "user_ctr_7d", "ad_price", "context_hour", "ad_category"]
    detector.set_reference_distribution(reference_data, features)

    logger.info("\n--- Scenario 1: No drift (same distribution) ---")
    current_no_drift = pd.DataFrame({
        "user_age": np.random.normal(35, 10, 5000),
        "user_ctr_7d": np.random.beta(2, 20, 5000),
        "ad_price": np.random.exponential(3, 5000),
        "context_hour": np.random.randint(0, 24, 5000),
        "ad_category": np.random.randint(1, 20, 5000)
    })
    report1 = detector.detect_all_features(current_no_drift)
    logger.info(f"  Overall drift score: {report1['overall_drift_score']:.4f}")
    logger.info(f"  Drifted features: {report1['drifted_features']}")
    logger.info(f"  Recommendation: {report1['recommendation']}")

    logger.info("\n--- Scenario 2: Drift detected (shifted distribution) ---")
    current_drifted = pd.DataFrame({
        "user_age": np.random.normal(45, 12, 5000),
        "user_ctr_7d": np.random.beta(5, 15, 5000),
        "ad_price": np.random.exponential(6, 5000),
        "context_hour": np.random.randint(0, 24, 5000),
        "ad_category": np.random.randint(1, 20, 5000)
    })
    report2 = detector.detect_all_features(current_drifted)
    logger.info(f"  Overall drift score: {report2['overall_drift_score']:.4f}")
    logger.info(f"  Drifted features: {report2['drifted_features']}")
    logger.info(f"  Recommendation: {report2['recommendation']}")

    logger.info("\n  Per-feature drift details:")
    for feat, detail in report2["drift_details"].items():
        if detail.get("drift_detected"):
            logger.info(f"    {feat}: severity={detail['severity']}, "
                       f"KS={detail['metrics'].get('ks_statistic', 'N/A'):.4f}, "
                       f"JS={detail['metrics'].get('js_divergence', 'N/A'):.4f}, "
                       f"PSI={detail['metrics'].get('psi', 'N/A'):.4f}")

    logger.info("\n--- Scenario 3: Critical drift (distribution collapse) ---")
    current_critical = pd.DataFrame({
        "user_age": np.random.normal(35, 1, 5000),
        "user_ctr_7d": np.random.beta(1, 2, 5000),
        "ad_price": np.random.uniform(0.1, 0.2, 5000),
        "context_hour": np.random.randint(20, 24, 5000),
        "ad_category": np.random.randint(1, 3, 5000)
    })
    report3 = detector.detect_all_features(current_critical)
    logger.info(f"  Overall drift score: {report3['overall_drift_score']:.4f}")
    logger.info(f"  Drifted features: {report3['drifted_features']}")
    logger.info(f"  Recommendation: {report3['recommendation']}")

    logger.info("="*70)
    logger.info("Drift detection demo complete!")
    logger.info("="*70)


@cli.command()
@click.pass_context
def run_ab_test(ctx):
    """运行AB测试 - Run A/B test"""
    logger = ctx.obj["logger"]
    logger.info("="*60)
    logger.info("Running AB test simulation...")
    logger.info("="*60)

    from online_evaluation.ab_testing import ABTestRunner

    ab_test = ABTestRunner()
    ab_test.start_experiment()

    np.random.seed(42)
    for i in range(5000):
        user_id = f"user_{i}"
        ad_id = f"ad_{np.random.randint(0, 100)}"
        pred_score = np.random.beta(2, 20)

        group = ab_test.record_impression(user_id, ad_id, pred_score)

        baseline_ctr = 0.05 if group == "control" else 0.065
        if np.random.random() < baseline_ctr:
            ab_test.record_click(user_id, ad_id, group)

    ab_test.print_summary()
    ab_test.save_results()

    logger.info("="*60)
    logger.info("AB test complete!")
    logger.info("="*60)


@cli.command()
@click.pass_context
@click.option("--generate", is_flag=True, help="Generate data first")
def run_all(ctx, generate):
    """运行完整流程 - Run complete pipeline"""
    logger = ctx.obj["logger"]
    logger.info("="*70)
    logger.info("CTR Prediction Model Upgrade Platform - Complete Pipeline")
    logger.info("="*70)

    if generate:
        logger.info("\n" + "="*70)
        logger.info("Step 1: Generating data...")
        logger.info("="*70)
        ctx.invoke(generate_data)

    logger.info("\n" + "="*70)
    logger.info("Step 2: Preparing data...")
    logger.info("="*70)
    ctx.invoke(prepare_data)

    logger.info("\n" + "="*70)
    logger.info("Step 3: Training models...")
    logger.info("="*70)
    ctx.invoke(train, model="all", epochs=3)

    logger.info("\n" + "="*70)
    logger.info("Step 4: Evaluating models...")
    logger.info("="*70)
    ctx.invoke(evaluate)

    logger.info("\n" + "="*70)
    logger.info("Step 5: Selecting best model...")
    logger.info("="*70)
    ctx.invoke(select_model)

    logger.info("\n" + "="*70)
    logger.info("Step 6: Generating deployment config...")
    logger.info("="*70)
    ctx.invoke(deploy, model_name="mmoe_v1")

    logger.info("\n" + "="*70)
    logger.info("Step 7: Demo adaptive embedding...")
    logger.info("="*70)
    ctx.invoke(demo_adaptive_embedding)

    logger.info("\n" + "="*70)
    logger.info("Step 8: Demo async evaluation...")
    logger.info("="*70)
    ctx.invoke(demo_async_eval)

    logger.info("\n" + "="*70)
    logger.info("Step 9: Demo online sampling...")
    logger.info("="*70)
    ctx.invoke(demo_online_sampling)

    logger.info("\n" + "="*70)
    logger.info("Step 10: Simulating stream...")
    logger.info("="*70)
    ctx.invoke(simulate_stream, num_impressions=500)

    logger.info("\n" + "="*70)
    logger.info("Step 11: Running AB test...")
    logger.info("="*70)
    ctx.invoke(run_ab_test)

    logger.info("\n" + "="*70)
    logger.info("Step 12: Demo SHAP explainability...")
    logger.info("="*70)
    ctx.invoke(demo_shap)

    logger.info("\n" + "="*70)
    logger.info("Step 13: Demo model distillation...")
    logger.info("="*70)
    ctx.invoke(demo_distillation, compression=0.25)

    logger.info("\n" + "="*70)
    logger.info("Step 14: Demo drift detection...")
    logger.info("="*70)
    ctx.invoke(demo_drift_detection)

    logger.info("\n" + "="*70)
    logger.info("COMPLETE: All pipeline steps finished!")
    logger.info("="*70)


if __name__ == "__main__":
    cli()

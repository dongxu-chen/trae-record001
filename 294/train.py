import os
import sys
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from src.data.preprocess import build_vocab_from_data, preprocess_video_features, preprocess_user_features
from src.data.data_generator import generate_sample_data, split_train_test, extract_multi_target_labels, print_label_stats
from src.data.cold_start import ColdStartHandler
from src.models.deepfm import create_fm_model, create_deepfm_model, save_model, predict_multi_target
from src.models.feature_importance import FeatureImportanceAnalyzer


def prepare_features(df, title_processor=None, tag_processor=None, user_processor=None, fit_processor=True):
    if fit_processor:
        title_processor, tag_processor = build_vocab_from_data(df)
    
    video_features = preprocess_video_features(df, title_processor, tag_processor)
    
    if fit_processor:
        user_features, user_processor = preprocess_user_features(df, None)
    else:
        user_features, _ = preprocess_user_features(df, user_processor)
    
    features = {}
    features.update(video_features)
    features.update(user_features)
    
    return features, title_processor, tag_processor, user_processor


def evaluate_multi_target(model, features, labels, name="Test"):
    predictions = model.predict(features, verbose=0)
    
    print(f"\n{name} Set Evaluation:")
    
    for i, target in enumerate(config.MULTI_TARGET[:model.num_tasks]):
        if labels.ndim == 2 and labels.shape[1] > i:
            y_true = labels[:, i]
        else:
            y_true = labels
        
        y_pred = predictions[:, i] if predictions.ndim == 2 else predictions
        
        try:
            from sklearn.metrics import roc_auc_score, accuracy_score
            auc = roc_auc_score(y_true, y_pred)
            acc = accuracy_score(y_true, (y_pred > 0.5).astype(int))
            print(f"  {target:6s} - AUC: {auc:.4f}, Accuracy: {acc:.4f}")
        except:
            print(f"  {target:6s} - AUC calculation skipped")


def train_two_stage(model_version='v1', num_tasks=3):
    print("=" * 60)
    print(f"Two-Stage Training - Multi-Target: {config.MULTI_TARGET[:num_tasks]}")
    print("=" * 60)
    
    model_save_path = os.path.join(config.MODEL_DIR, model_version)
    print(f"\nModel will be saved to: {model_save_path}")
    
    print("\n1. Generating/Loading sample data...")
    data_path = os.path.join(config.DATA_DIR, "sample_data.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        if 'like' not in df.columns or 'share' not in df.columns:
            print("Regenerating multi-target labels...")
            df = generate_sample_data(num_samples=20000, save_path=data_path, multi_target=True)
        print(f"Loaded existing data: {len(df)} samples")
    else:
        df = generate_sample_data(num_samples=20000, save_path=data_path, multi_target=True)
    
    print_label_stats(df)
    
    print("\n2. Splitting train/test data...")
    train_df, test_df = split_train_test(df, test_ratio=0.2)
    print(f"Train samples: {len(train_df)}, Test samples: {len(test_df)}")
    
    print("\n3. Preprocessing features...")
    train_features, title_processor, tag_processor, user_processor = prepare_features(
        train_df, fit_processor=True
    )
    test_features, _, _, _ = prepare_features(
        test_df, title_processor, tag_processor, user_processor, fit_processor=False
    )
    
    train_labels = extract_multi_target_labels(train_df)[:, :num_tasks]
    test_labels = extract_multi_target_labels(test_df)[:, :num_tasks]
    
    print(f"Feature shapes:")
    for k, v in train_features.items():
        print(f"  {k}: {v.shape}")
    print(f"Labels shape: {train_labels.shape}")
    
    print("\n" + "=" * 60)
    print("Stage 1: FM Pretraining")
    print("=" * 60)
    
    print("\n4. Building FM model...")
    fm_model = create_fm_model(num_tasks=num_tasks)
    
    print("\n5. Training FM model...")
    fm_callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_auc',
            patience=3,
            mode='max',
            restore_best_weights=True
        )
    ]
    
    fm_history = fm_model.fit(
        train_features,
        train_labels,
        batch_size=config.BATCH_SIZE,
        epochs=config.FM_PRETRAIN_EPOCHS,
        validation_split=0.1,
        callbacks=fm_callbacks,
        verbose=1
    )
    
    print("\n6. Evaluating FM model...")
    evaluate_multi_target(fm_model, test_features, test_labels, "FM Test")
    
    print("\n7. Extracting pretrained FM embeddings...")
    pretrained_embeddings = fm_model.get_embedding_weights()
    print(f"Pretrained embeddings for: {list(pretrained_embeddings.keys())}")
    
    print("\n" + "=" * 60)
    print("Stage 2: DeepFM Joint Training")
    print("=" * 60)
    
    print("\n8. Building DeepFM model with pretrained embeddings...")
    deepfm_model = create_deepfm_model(pretrained_embeddings=pretrained_embeddings, num_tasks=num_tasks)
    
    print("\n9. Phase 1 - Training DNN layers (FM layers frozen)...")
    deepfm_model.freeze_fm_layers()
    
    phase1_epochs = max(3, config.EPOCHS // 2)
    phase1_history = deepfm_model.fit(
        train_features,
        train_labels,
        batch_size=config.BATCH_SIZE,
        epochs=phase1_epochs,
        validation_split=0.1,
        callbacks=fm_callbacks,
        verbose=1
    )
    
    print("\n10. Phase 2 - Fine-tuning all layers...")
    deepfm_model.unfreeze_fm_layers()
    
    deepfm_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.LEARNING_RATE * 0.1),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    
    phase2_epochs = config.EPOCHS - phase1_epochs
    phase2_history = deepfm_model.fit(
        train_features,
        train_labels,
        batch_size=config.BATCH_SIZE,
        epochs=phase2_epochs,
        validation_split=0.1,
        callbacks=fm_callbacks,
        verbose=1
    )
    
    print("\n11. Evaluating DeepFM model...")
    evaluate_multi_target(deepfm_model, test_features, test_labels, "DeepFM Test")
    
    print("\n12. Building ColdStartHandler...")
    cold_start_handler = ColdStartHandler()
    cold_start_handler.fit(train_df)
    
    print("\n13. Running Feature Importance Analysis...")
    analyzer = FeatureImportanceAnalyzer(deepfm_model)
    analyzer.combined_importance(
        test_features, 
        test_labels if test_labels.ndim == 1 else test_labels[:, 0],
        target='click'
    )
    analyzer.print_report(target='click')
    
    print("\n14. Saving model and artifacts...")
    save_model(deepfm_model, model_save_path, model_type='deepfm')
    
    processors = {
        'title_processor': title_processor,
        'tag_processor': tag_processor,
        'user_processor': user_processor
    }
    
    with open(os.path.join(model_save_path, 'processors.pkl'), 'wb') as f:
        pickle.dump(processors, f)
    
    cold_start_handler.save(os.path.join(model_save_path, 'cold_start.pkl'))
    
    feature_report_path = os.path.join(model_save_path, 'feature_importance.npy')
    analyzer.save_report(feature_report_path, test_features, test_labels)
    
    print("\n" + "=" * 60)
    print(f"Two-stage training completed! Model version: {model_version}")
    print("=" * 60)
    
    return deepfm_model, processors, cold_start_handler


def train_baseline(model_version='baseline', num_tasks=3):
    print("=" * 60)
    print(f"Baseline Training - Multi-Target: {config.MULTI_TARGET[:num_tasks]}")
    print("=" * 60)
    
    model_save_path = os.path.join(config.MODEL_DIR, model_version)
    
    print("\n1. Generating/Loading sample data...")
    data_path = os.path.join(config.DATA_DIR, "sample_data.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        df = generate_sample_data(num_samples=20000, save_path=data_path, multi_target=True)
    
    train_df, test_df = split_train_test(df, test_ratio=0.2)
    
    train_features, title_processor, tag_processor, user_processor = prepare_features(
        train_df, fit_processor=True
    )
    test_features, _, _, _ = prepare_features(
        test_df, title_processor, tag_processor, user_processor, fit_processor=False
    )
    
    train_labels = extract_multi_target_labels(train_df)[:, :num_tasks]
    test_labels = extract_multi_target_labels(test_df)[:, :num_tasks]
    
    print("\n2. Building DeepFM from scratch...")
    model = create_deepfm_model(num_tasks=num_tasks)
    
    print("\n3. Training...")
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_auc',
            patience=3,
            mode='max',
            restore_best_weights=True
        )
    ]
    
    history = model.fit(
        train_features,
        train_labels,
        batch_size=config.BATCH_SIZE,
        epochs=config.EPOCHS,
        validation_split=0.1,
        callbacks=callbacks,
        verbose=1
    )
    
    print("\n4. Evaluating...")
    evaluate_multi_target(model, test_features, test_labels, "Test")
    
    print("\n5. Saving...")
    save_model(model, model_save_path, model_type='deepfm')
    
    processors = {
        'title_processor': title_processor,
        'tag_processor': tag_processor,
        'user_processor': user_processor
    }
    
    with open(os.path.join(model_save_path, 'processors.pkl'), 'wb') as f:
        pickle.dump(processors, f)
    
    cold_start_handler = ColdStartHandler()
    cold_start_handler.fit(train_df)
    cold_start_handler.save(os.path.join(model_save_path, 'cold_start.pkl'))
    
    print("\nBaseline training completed!")
    return model, processors, cold_start_handler


def predict_example():
    print("\n" + "=" * 60)
    print("Multi-Target Prediction Example")
    print("=" * 60)
    
    model_version = 'v1'
    model_path = os.path.join(config.MODEL_DIR, model_version)
    processor_path = os.path.join(model_path, 'processors.pkl')
    
    if not os.path.exists(processor_path):
        print("No trained model found. Please run training first.")
        return
    
    from src.models.deepfm import load_model
    model = load_model(model_path, num_tasks=len(config.MULTI_TARGET))
    
    with open(processor_path, 'rb') as f:
        processors = pickle.load(f)
    
    example_data = [
        {
            "user_id": "user_123",
            "video_id": "video_456",
            "title": "Python机器学习入门教程",
            "tags": "Python,机器学习,AI",
            "category": "科技",
            "duration": 300,
            "user_history": "video_100,video_200,video_300"
        },
        {
            "user_id": "new_user_999",
            "video_id": "video_789",
            "title": "游戏精彩操作集锦",
            "tags": "游戏,电竞,精彩",
            "category": "游戏",
            "duration": 180,
            "user_history": ""
        }
    ]
    
    title_processor = processors['title_processor']
    tag_processor = processors['tag_processor']
    user_processor = processors['user_processor']
    
    print("\nPredicting multi-target probabilities:")
    for i, example in enumerate(example_data):
        from src.data.preprocess import preprocess_video_features, preprocess_user_features
        
        df_example = pd.DataFrame([example])
        
        video_features = preprocess_video_features(df_example, title_processor, tag_processor)
        user_features, _ = preprocess_user_features(df_example, user_processor)
        
        features = {}
        features.update(video_features)
        features.update(user_features)
        
        predictions = predict_multi_target(model, features)
        
        print(f"\nExample {i+1}:")
        print(f"  User: {example['user_id']}")
        print(f"  Title: {example['title']}")
        for target in config.MULTI_TARGET:
            prob = predictions.get(target, [0])[0]
            print(f"  {target:6s}: {prob:.4f} ({prob*100:.2f}%)")


if __name__ == "__main__":
    num_tasks = len(config.MULTI_TARGET)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'predict':
            predict_example()
        elif sys.argv[1] == 'baseline':
            version = sys.argv[2] if len(sys.argv) > 2 else 'baseline'
            train_baseline(model_version=version, num_tasks=num_tasks)
        elif sys.argv[1] == 'twostage':
            version = sys.argv[2] if len(sys.argv) > 2 else 'v1'
            train_two_stage(model_version=version, num_tasks=num_tasks)
        elif sys.argv[1] == 'singletask':
            version = sys.argv[2] if len(sys.argv) > 2 else 'v1_single'
            train_two_stage(model_version=version, num_tasks=1)
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        train_two_stage(model_version='v1', num_tasks=num_tasks)
        train_baseline(model_version='v2', num_tasks=num_tasks)
        predict_example()

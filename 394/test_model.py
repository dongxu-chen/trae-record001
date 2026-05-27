import sys
sys.path.insert(0, '.')
from src.models import SleepStageClassifier, SleepQualityAnalyzer, FactorAnalyzer
from src.features import SleepDataGenerator

print('模块导入成功!')

generator = SleepDataGenerator(n_subjects=2, n_nights=1, n_epochs=100)
data = generator.generate_all_data()
print(f'生成数据成功: {len(data)} 条')

classifier = SleepStageClassifier()
X, y = classifier.prepare_dataset(data)
print(f'特征提取成功: X shape = {X.shape}, y shape = {y.shape}')

results = classifier.train(X, y)
test_acc = results['test_accuracy']
print(f'训练成功! 测试准确率: {test_acc:.4f}')

classifier.save_model('models')
print('模型保存成功!')

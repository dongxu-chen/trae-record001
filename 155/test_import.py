from hsi_classification import PCA, SVMClassifier, CNNClassifier
from hsi_classification import CNN3DClassifier, TransferLearningClassifier
from hsi_classification import ActiveLearning, ClassificationVisualizer, Metrics
import hsi_classification

print('所有模块导入成功!')
print(f'PCA: {PCA}')
print(f'SVMClassifier: {SVMClassifier}')
print(f'CNNClassifier: {CNNClassifier}')
print(f'CNN3DClassifier: {CNN3DClassifier}')
print(f'TransferLearningClassifier: {TransferLearningClassifier}')
print(f'ActiveLearning: {ActiveLearning}')
print(f'ClassificationVisualizer: {ClassificationVisualizer}')
print(f'Metrics: {Metrics}')
print(f'库版本: v{hsi_classification.__version__}')
print('\n✅ 所有模块导入成功!')

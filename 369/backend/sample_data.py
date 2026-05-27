import sys
import asyncio
import httpx
from datetime import datetime

SAMPLE_DOCUMENTS = [
    {"doc_id": "doc_001", "title": "Python 编程入门指南", "content": "Python 是一种简单易学的编程语言，广泛应用于数据分析、人工智能、Web开发等领域。本书从基础语法开始，循序渐进地介绍 Python 的核心概念和实践技巧。"},
    {"doc_id": "doc_002", "title": "机器学习实战教程", "content": "本书详细介绍了机器学习的核心算法，包括监督学习、非监督学习、深度学习等。通过大量实例帮助读者掌握 scikit-learn、TensorFlow 等工具的使用。"},
    {"doc_id": "doc_003", "title": "Elasticsearch 搜索引擎开发", "content": "Elasticsearch 是一个分布式全文搜索引擎，提供强大的搜索和分析功能。本书介绍了 ES 的架构设计、索引管理、查询优化等核心技术。"},
    {"doc_id": "doc_004", "title": "深度学习与神经网络", "content": "神经网络是深度学习的基础，本书从感知机开始，逐步深入讲解卷积神经网络、循环神经网络、Transformer 等前沿模型。"},
    {"doc_id": "doc_005", "title": "数据分析与可视化", "content": "使用 Python 进行数据分析的完整指南，涵盖数据清洗、统计分析、数据可视化等内容。介绍 Pandas、NumPy、Matplotlib 等库的使用。"},
    {"doc_id": "doc_006", "title": "Web 开发框架 Flask 实战", "content": "Flask 是一个轻量级的 Python Web 框架，本书介绍如何使用 Flask 构建 RESTful API，包括路由设计、数据库集成、认证授权等。"},
    {"doc_id": "doc_007", "title": "自然语言处理技术详解", "content": "自然语言处理（NLP）是人工智能的重要分支，本书介绍了词向量、文本分类、情感分析、机器翻译等 NLP 核心技术。"},
    {"doc_id": "doc_008", "title": "数据库原理与 SQL 优化", "content": "数据库是后端开发的核心，本书讲解了关系型数据库的设计原理，以及 SQL 查询优化的各种技巧和最佳实践。"},
    {"doc_id": "doc_009", "title": "计算机视觉基础", "content": "计算机视觉让机器能够理解图像内容，本书介绍了图像处理、特征提取、目标检测、图像分割等核心算法。"},
    {"doc_id": "doc_010", "title": "推荐系统设计与实现", "content": "推荐系统是电商和内容平台的核心技术，本书讲解了协同过滤、内容推荐、深度学习推荐等算法的设计与实现。"},
    {"doc_id": "doc_011", "title": "Java 核心技术卷", "content": "Java 是企业级开发的主流语言，本书全面介绍了 Java 语言的核心特性，包括面向对象、异常处理、多线程编程等。"},
    {"doc_id": "doc_012", "title": "前端开发 React 实战", "content": "React 是流行的前端框架，本书介绍组件化开发、状态管理、路由配置等核心概念，并通过实际项目掌握 React 开发。"},
    {"doc_id": "doc_013", "title": "分布式系统原理", "content": "分布式系统是现代大型应用的基础，本书讲解了一致性协议、数据复制、容错机制等分布式系统核心理论。"},
    {"doc_id": "doc_014", "title": "算法设计与分析", "content": "算法是程序员的基本功，本书详细讲解了排序、搜索、动态规划、贪心算法等经典算法及其时间复杂度分析。"},
    {"doc_id": "doc_015", "title": "云计算与容器技术", "content": "云计算和容器化改变了应用部署方式，本书介绍 Docker、Kubernetes 等容器编排技术，以及云平台的使用。"},
]

SAMPLE_QUERIES = [
    {"query_id": "q_001", "query_text": "Python 编程基础", "description": "查找 Python 编程入门相关的文档", "query_type": "informational"},
    {"query_id": "q_002", "query_text": "机器学习算法", "description": "查找机器学习相关算法教程", "query_type": "informational"},
    {"query_id": "q_003", "query_text": "Elasticsearch 查询优化", "description": "查找搜索引擎优化相关内容", "query_type": "transactional"},
    {"query_id": "q_004", "query_text": "深度学习神经网络", "description": "查找深度学习和神经网络相关内容", "query_type": "exploratory"},
    {"query_id": "q_005", "query_text": "数据分析 Pandas", "description": "查找数据分析工具 Pandas 相关文档", "query_type": "navigational"},
    {"query_id": "q_006", "query_text": "推荐系统设计", "description": "查找推荐系统相关的技术文档", "query_type": "transactional"},
    {"query_id": "q_007", "query_text": "前端 React 开发", "description": "查找 React 前端框架相关文档", "query_type": "informational"},
]

SAMPLE_ANNOTATIONS = [
    {"query_id": "q_001", "doc_id": "doc_001", "relevance": 3},
    {"query_id": "q_001", "doc_id": "doc_005", "relevance": 2},
    {"query_id": "q_001", "doc_id": "doc_006", "relevance": 1},
    {"query_id": "q_002", "doc_id": "doc_002", "relevance": 3},
    {"query_id": "q_002", "doc_id": "doc_004", "relevance": 2},
    {"query_id": "q_002", "doc_id": "doc_010", "relevance": 2},
    {"query_id": "q_003", "doc_id": "doc_003", "relevance": 3},
    {"query_id": "q_003", "doc_id": "doc_008", "relevance": 1},
    {"query_id": "q_004", "doc_id": "doc_004", "relevance": 3},
    {"query_id": "q_004", "doc_id": "doc_002", "relevance": 2},
    {"query_id": "q_004", "doc_id": "doc_007", "relevance": 2},
    {"query_id": "q_005", "doc_id": "doc_005", "relevance": 3},
    {"query_id": "q_005", "doc_id": "doc_001", "relevance": 2},
    {"query_id": "q_006", "doc_id": "doc_010", "relevance": 3},
    {"query_id": "q_006", "doc_id": "doc_002", "relevance": 1},
    {"query_id": "q_007", "doc_id": "doc_012", "relevance": 3},
    {"query_id": "q_007", "doc_id": "doc_006", "relevance": 1},
]

API_BASE = "http://localhost:8000/api"


async def import_sample_data():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            health = await client.get(f"{API_BASE}/health")
            print(f"API Health: {health.json()}")
        except Exception as e:
            print(f"无法连接到 API 服务器: {e}")
            print("请先启动后端服务: cd backend && python main.py")
            sys.exit(1)

        print("\n=== 导入示例文档 ===")
        docs_response = await client.post(f"{API_BASE}/documents/batch", json=SAMPLE_DOCUMENTS)
        print(f"文档导入结果: {docs_response.json()}")

        print("\n=== 导入示例查询 ===")
        queries_response = await client.post(f"{API_BASE}/queries/batch", json=SAMPLE_QUERIES)
        print(f"查询导入结果: {queries_response.json()}")

        print("\n=== 导入示例标注 ===")
        annotations_response = await client.post(
            f"{API_BASE}/annotations/batch",
            json={"query_id": "batch", "annotations": SAMPLE_ANNOTATIONS}
        )
        print(f"标注导入结果: {annotations_response.json()}")

        print("\n=== 运行示例评估 ===")
        for query in SAMPLE_QUERIES[:2]:
            eval_response = await client.post(
                f"{API_BASE}/evaluate",
                json={"query_text": query["query_text"], "model_name": "default", "k": 10}
            )
            result = eval_response.json()
            metrics = result["metrics"]
            print(f"\n查询: {query['query_text']}")
            print(f"  Recall@10: {metrics['recall_at_k']:.4f}")
            print(f"  Precision@10: {metrics['precision_at_k']:.4f}")
            print(f"  NDCG@10: {metrics['ndcg_at_k']:.4f}")
            print(f"  Hit Rate: {metrics['hit_rate']:.4f}")

        print("\n=== 示例数据导入完成 ===")
        print(f"共导入 {len(SAMPLE_DOCUMENTS)} 个文档")
        print(f"共导入 {len(SAMPLE_QUERIES)} 个查询")
        print(f"共导入 {len(SAMPLE_ANNOTATIONS)} 个标注")


if __name__ == "__main__":
    asyncio.run(import_sample_data())

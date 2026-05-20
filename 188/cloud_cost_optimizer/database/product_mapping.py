import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ProductCategory:
    """统一产品分类"""
    category_code: str
    category_name: str
    description: str = ""
    parent_category: Optional[str] = None


@dataclass
class UnifiedProduct:
    """统一产品定义"""
    product_code: str
    product_name: str
    category: ProductCategory
    billing_unit: str = ""
    is_compute: bool = False
    is_storage: bool = False
    is_network: bool = False
    is_database: bool = False
    is_managed: bool = False


class ProductMapper:
    """云厂商产品名称统一映射器"""

    # 产品分类定义
    CATEGORIES = {
        "compute": ProductCategory("compute", "计算服务", "云服务器、容器等计算资源"),
        "compute_vm": ProductCategory("compute_vm", "虚拟机", "弹性云服务器", "compute"),
        "compute_container": ProductCategory("compute_container", "容器服务", "Kubernetes、容器实例", "compute"),
        "compute_serverless": ProductCategory("compute_serverless", "无服务器", "函数计算、Serverless", "compute"),

        "storage": ProductCategory("storage", "存储服务", "各类存储服务"),
        "storage_object": ProductCategory("storage_object", "对象存储", "S3、OSS、COS等", "storage"),
        "storage_block": ProductCategory("storage_block", "块存储", "云硬盘、EBS等", "storage"),
        "storage_file": ProductCategory("storage_file", "文件存储", "NAS、EFS等", "storage"),
        "storage_archive": ProductCategory("storage_archive", "归档存储", "冷存储、归档存储", "storage"),

        "database": ProductCategory("database", "数据库服务", "各类数据库服务"),
        "database_relational": ProductCategory("database_relational", "关系型数据库", "MySQL、PostgreSQL等", "database"),
        "database_nosql": ProductCategory("database_nosql", "NoSQL数据库", "Redis、MongoDB等", "database"),
        "database_warehouse": ProductCategory("database_warehouse", "数据仓库", "大数据分析", "database"),

        "network": ProductCategory("network", "网络服务", "网络相关服务"),
        "network_loadbalancer": ProductCategory("network_loadbalancer", "负载均衡", "ELB、SLB、CLB等", "network"),
        "network_cdn": ProductCategory("network_cdn", "CDN加速", "内容分发网络", "network"),
        "network_vpc": ProductCategory("network_vpc", "VPC网络", "专有网络、网关", "network"),

        "security": ProductCategory("security", "安全服务", "安全相关服务"),
        "monitoring": ProductCategory("monitoring", "监控运维", "监控、日志等"),
        "analytics": ProductCategory("analytics", "数据分析", "大数据分析服务"),
        "ai_ml": ProductCategory("ai_ml", "AI/机器学习", "人工智能相关服务"),
        "other": ProductCategory("other", "其他服务", "未分类的服务"),
    }

    # 云厂商产品映射表
    PRODUCT_MAPPING = {
        "AWS": {
            # 计算
            "Amazon Elastic Compute Cloud - Compute": ("compute_vm", "EC2云服务器", "Hours"),
            "Amazon EC2": ("compute_vm", "EC2云服务器", "Hours"),
            "AWS Lambda": ("compute_serverless", "Lambda函数计算", "Requests"),
            "Amazon ECS": ("compute_container", "ECS容器服务", "Hours"),
            "Amazon EKS": ("compute_container", "EKS容器服务", "Hours"),
            "AWS Fargate": ("compute_container", "Fargate无服务器容器", "vCPU-Hours"),

            # 存储
            "Amazon Simple Storage Service": ("storage_object", "S3对象存储", "GB-Month"),
            "Amazon S3": ("storage_object", "S3对象存储", "GB-Month"),
            "Amazon Elastic Block Store": ("storage_block", "EBS块存储", "GB-Month"),
            "Amazon EFS": ("storage_file", "EFS文件存储", "GB-Month"),
            "Amazon Glacier": ("storage_archive", "Glacier归档存储", "GB-Month"),

            # 数据库
            "Amazon Relational Database Service": ("database_relational", "RDS关系型数据库", "Hours"),
            "Amazon RDS": ("database_relational", "RDS关系型数据库", "Hours"),
            "Amazon DynamoDB": ("database_nosql", "DynamoDB NoSQL", "ReadCapacityUnits"),
            "Amazon ElastiCache": ("database_nosql", "ElastiCache缓存", "Hours"),
            "Amazon Redshift": ("database_warehouse", "Redshift数据仓库", "Hours"),

            # 网络
            "Amazon Elastic Load Balancing": ("network_loadbalancer", "ELB负载均衡", "Hours"),
            "Amazon CloudFront": ("network_cdn", "CloudFront CDN", "GB"),
            "Amazon VPC": ("network_vpc", "VPC专有网络", "Hours"),
            "AWS Direct Connect": ("network_vpc", "Direct Connect专线", "Hours"),

            # 安全
            "AWS Shield": ("security", "Shield防护", "GB"),
            "AWS WAF": ("security", "WAF防火墙", "Rules"),

            # 监控
            "Amazon CloudWatch": ("monitoring", "CloudWatch监控", "Metrics"),
            "AWS CloudTrail": ("monitoring", "CloudTrail审计", "Events"),

            # 分析
            "Amazon Athena": ("analytics", "Athena数据查询", "TB-Scanned"),
            "Amazon EMR": ("analytics", "EMR大数据", "Hours"),
            "Amazon Kinesis": ("analytics", "Kinesis数据流", "GB"),

            # AI/ML
            "Amazon SageMaker": ("ai_ml", "SageMaker机器学习", "Hours"),
            "Amazon Rekognition": ("ai_ml", "Rekognition图像识别", "Images"),
        },

        "阿里云": {
            # 计算
            "云服务器ECS": ("compute_vm", "ECS云服务器", "Hours"),
            "弹性计算服务": ("compute_vm", "ECS云服务器", "Hours"),
            "函数计算": ("compute_serverless", "函数计算FC", "GB-Seconds"),
            "容器服务Kubernetes版": ("compute_container", "ACK容器服务", "Nodes"),
            "弹性容器实例": ("compute_container", "ECI弹性容器实例", "vCPU-Hours"),
            "轻量应用服务器": ("compute_vm", "轻量应用服务器", "Hours"),

            # 存储
            "对象存储OSS": ("storage_object", "OSS对象存储", "GB-Month"),
            "云服务器 ECS": ("compute_vm", "ECS云服务器", "Hours"),
            "块存储": ("storage_block", "块存储EBS", "GB-Month"),
            "云盘": ("storage_block", "云盘", "GB-Month"),
            "文件存储NAS": ("storage_file", "NAS文件存储", "GB-Month"),
            "归档存储": ("storage_archive", "归档存储OAS", "GB-Month"),
            "冷存储": ("storage_archive", "冷存储", "GB-Month"),

            # 数据库
            "云数据库RDS": ("database_relational", "RDS关系型数据库", "Hours"),
            "云数据库MySQL": ("database_relational", "RDS MySQL", "Hours"),
            "云数据库PostgreSQL": ("database_relational", "RDS PostgreSQL", "Hours"),
            "云数据库Redis": ("database_nosql", "云数据库Redis", "Hours"),
            "云数据库MongoDB": ("database_nosql", "云数据库MongoDB", "Hours"),
            "云数据库ClickHouse": ("database_warehouse", "ClickHouse数仓", "Hours"),
            "云原生数据库PolarDB": ("database_relational", "PolarDB云原生数据库", "Hours"),

            # 网络
            "负载均衡SLB": ("network_loadbalancer", "SLB负载均衡", "Hours"),
            "CDN": ("network_cdn", "CDN加速", "GB"),
            "全站加速": ("network_cdn", "全站加速DCDN", "GB"),
            "专有网络VPC": ("network_vpc", "VPC专有网络", "Hours"),
            "高速通道": ("network_vpc", "高速通道", "Hours"),
            "共享带宽": ("network", "共享带宽", "Mbps-Month"),
            "弹性公网IP": ("network", "弹性公网IP", "Hours"),

            # 安全
            "云安全中心": ("security", "云安全中心", "Assets"),
            "Web应用防火墙": ("security", "WAF防火墙", "Domains"),
            "DDoS防护": ("security", "DDoS防护", "GB"),

            # 监控
            "云监控": ("monitoring", "云监控CMS", "Metrics"),
            "日志服务SLS": ("monitoring", "日志服务SLS", "GB"),

            # 分析
            "MaxCompute": ("analytics", "MaxCompute大数据计算", "CU-Hours"),
            "E-MapReduce": ("analytics", "E-MapReduce大数据", "Hours"),
            "实时计算Flink": ("analytics", "实时计算Flink", "CU-Hours"),

            # AI/ML
            "机器学习PAI": ("ai_ml", "机器学习PAI", "CU-Hours"),
            "图像识别": ("ai_ml", "图像识别", "Images"),
            "语音识别": ("ai_ml", "语音识别ASR", "Minutes"),
        },

        "腾讯云": {
            # 计算
            "云服务器CVM": ("compute_vm", "CVM云服务器", "Hours"),
            "云服务器": ("compute_vm", "CVM云服务器", "Hours"),
            "云函数SCF": ("compute_serverless", "SCF云函数", "GB-Seconds"),
            "容器服务TKE": ("compute_container", "TKE容器服务", "Nodes"),
            "弹性容器服务EKS": ("compute_container", "EKS弹性容器", "vCPU-Hours"),
            "轻量应用服务器Lighthouse": ("compute_vm", "轻量应用服务器", "Hours"),

            # 存储
            "对象存储COS": ("storage_object", "COS对象存储", "GB-Month"),
            "云硬盘CBS": ("storage_block", "CBS云硬盘", "GB-Month"),
            "文件存储CFS": ("storage_file", "CFS文件存储", "GB-Month"),
            "归档存储CAS": ("storage_archive", "CAS归档存储", "GB-Month"),
            "存储网关CSG": ("storage", "存储网关CSG", "Hours"),

            # 数据库
            "云数据库MySQL": ("database_relational", "CDB MySQL", "Hours"),
            "云数据库CDB": ("database_relational", "CDB关系型数据库", "Hours"),
            "云数据库PostgreSQL": ("database_relational", "PostgreSQL", "Hours"),
            "云数据库Redis": ("database_nosql", "云数据库Redis", "Hours"),
            "云数据库MongoDB": ("database_nosql", "云数据库MongoDB", "Hours"),
            "云数据库ClickHouse": ("database_warehouse", "ClickHouse数仓", "Hours"),
            "分布式数据库TDSQL": ("database_relational", "TDSQL分布式数据库", "Hours"),

            # 网络
            "负载均衡CLB": ("network_loadbalancer", "CLB负载均衡", "Hours"),
            "内容分发网络CDN": ("network_cdn", "CDN加速", "GB"),
            "全站加速网络ECDN": ("network_cdn", "ECDN全站加速", "GB"),
            "私有网络VPC": ("network_vpc", "VPC私有网络", "Hours"),
            "对等连接": ("network_vpc", "对等连接", "Hours"),
            "弹性公网IP": ("network", "弹性公网IP EIP", "Hours"),
            "共享带宽包": ("network", "共享带宽包", "Mbps-Month"),

            # 安全
            "Web应用防火墙WAF": ("security", "WAF防火墙", "Domains"),
            "DDoS高防": ("security", "DDoS高防", "GB"),
            "主机安全": ("security", "主机安全CWP", "Assets"),
            "安全运营中心": ("security", "安全运营中心SOC", "Assets"),

            # 监控
            "云监控": ("monitoring", "云监控", "Metrics"),
            "日志服务CLS": ("monitoring", "日志服务CLS", "GB"),

            # 分析
            "弹性MapReduce": ("analytics", "EMR大数据", "Hours"),
            "流计算Oceanus": ("analytics", "Oceanus流计算", "CU-Hours"),
            "数据湖计算DLC": ("analytics", "DLC数据湖计算", "CU-Hours"),
            "数据开发治理平台WeData": ("analytics", "WeData数据开发", "CU-Hours"),

            # AI/ML
            "智能钛机器学习TI-ONE": ("ai_ml", "TI-ONE机器学习", "CU-Hours"),
            "图像识别": ("ai_ml", "图像识别", "Images"),
            "语音识别ASR": ("ai_ml", "语音识别ASR", "Minutes"),
        },
    }

    def __init__(self):
        self._build_reverse_mapping()

    def _build_reverse_mapping(self):
        """构建反向映射，用于快速查找"""
        self._reverse_map = {}
        for provider, products in self.PRODUCT_MAPPING.items():
            for service_name, (category_code, unified_name, unit) in products.items():
                self._reverse_map[(provider, service_name)] = {
                    "category_code": category_code,
                    "unified_name": unified_name,
                    "billing_unit": unit,
                    "category": self.CATEGORIES[category_code],
                }

    def map_product(
        self,
        provider: str,
        service_name: str,
        product_code: str = "",
    ) -> Dict[str, Any]:
        """将云厂商产品名称映射为统一产品

        Args:
            provider: 云厂商名称 (AWS/阿里云/腾讯云)
            service_name: 服务名称
            product_code: 产品代码 (可选)

        Returns:
            统一产品信息字典
        """
        key = (provider, service_name)

        if key in self._reverse_map:
            mapping = self._reverse_map[key]
            return {
                "unified_product_code": mapping["category_code"],
                "unified_product_name": mapping["unified_name"],
                "category": mapping["category"].category_name,
                "category_code": mapping["category_code"],
                "parent_category": mapping["category"].parent_category,
                "billing_unit": mapping["billing_unit"],
                "is_compute": mapping["category_code"].startswith("compute"),
                "is_storage": mapping["category_code"].startswith("storage"),
                "is_network": mapping["category_code"].startswith("network"),
                "is_database": mapping["category_code"].startswith("database"),
                "is_managed": mapping["category_code"] in ["database_relational", "database_nosql", "ai_ml"],
                "mapping_found": True,
            }

        # 尝试模糊匹配
        fuzzy_match = self._fuzzy_match(provider, service_name)
        if fuzzy_match:
            return fuzzy_match

        # 返回未分类
        return {
            "unified_product_code": "other",
            "unified_product_name": service_name,
            "category": "其他服务",
            "category_code": "other",
            "parent_category": None,
            "billing_unit": "",
            "is_compute": False,
            "is_storage": False,
            "is_network": False,
            "is_database": False,
            "is_managed": False,
            "mapping_found": False,
        }

    def _fuzzy_match(self, provider: str, service_name: str) -> Optional[Dict[str, Any]]:
        """模糊匹配产品名称"""
        keywords = {
            "compute_vm": ["ECS", "EC2", "CVM", "云服务器", "弹性计算", "虚拟机"],
            "compute_container": ["容器", "Kubernetes", "EKS", "ACK", "TKE", "ECI"],
            "compute_serverless": ["函数", "Serverless", "Lambda", "无服务器"],
            "storage_object": ["对象存储", "S3", "OSS", "COS", "简单存储"],
            "storage_block": ["块存储", "EBS", "云盘", "CBS", "硬盘"],
            "storage_file": ["文件存储", "NAS", "EFS", "CFS"],
            "storage_archive": ["归档", "Glacier", "冷存储"],
            "database_relational": ["RDS", "CDB", "关系型", "MySQL", "PostgreSQL", "SQL Server"],
            "database_nosql": ["Redis", "MongoDB", "NoSQL", "DynamoDB", "缓存"],
            "database_warehouse": ["数仓", "数据仓库", "Redshift", "ClickHouse"],
            "network_loadbalancer": ["负载均衡", "ELB", "SLB", "CLB"],
            "network_cdn": ["CDN", "加速", "CloudFront"],
            "network_vpc": ["VPC", "私有网络", "专有网络"],
            "security": ["安全", "防火墙", "DDoS", "WAF"],
            "monitoring": ["监控", "日志", "CloudWatch", "云监控"],
            "analytics": ["分析", "大数据", "EMR", "MaxCompute", "MapReduce"],
            "ai_ml": ["AI", "机器学习", "图像识别", "语音识别", "PAI", "SageMaker"],
        }

        for category_code, keyword_list in keywords.items():
            for keyword in keyword_list:
                if keyword.lower() in service_name.lower():
                    category = self.CATEGORIES[category_code]
                    return {
                        "unified_product_code": category_code,
                        "unified_product_name": f"{category.category_name}({service_name})",
                        "category": category.category_name,
                        "category_code": category_code,
                        "parent_category": category.parent_category,
                        "billing_unit": "",
                        "is_compute": category_code.startswith("compute"),
                        "is_storage": category_code.startswith("storage"),
                        "is_network": category_code.startswith("network"),
                        "is_database": category_code.startswith("database"),
                        "is_managed": category_code in ["database_relational", "database_nosql", "ai_ml"],
                        "mapping_found": True,
                    }

        return None

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有产品分类"""
        return [
            {
                "category_code": code,
                "category_name": cat.category_name,
                "description": cat.description,
                "parent_category": cat.parent_category,
            }
            for code, cat in self.CATEGORIES.items()
        ]

    def get_category_products(self, category_code: str) -> List[str]:
        """获取某分类下的所有统一产品名称"""
        products = set()
        for mapping in self._reverse_map.values():
            if mapping["category_code"] == category_code:
                products.add(mapping["unified_name"])
        return list(products)

    def get_provider_products(self, provider: str) -> List[Dict[str, Any]]:
        """获取某云厂商的所有产品映射"""
        products = []
        for (prov, service_name), mapping in self._reverse_map.items():
            if prov == provider:
                products.append({
                    "original_service_name": service_name,
                    "unified_product_name": mapping["unified_name"],
                    "category": mapping["category"].category_name,
                    "category_code": mapping["category_code"],
                })
        return products

    def get_unmapped_services(
        self,
        provider: str,
        service_names: List[str],
    ) -> List[str]:
        """获取未匹配的服务名称"""
        unmapped = []
        for service_name in service_names:
            result = self.map_product(provider, service_name)
            if not result["mapping_found"]:
                unmapped.append(service_name)
        return unmapped

    def add_custom_mapping(
        self,
        provider: str,
        service_name: str,
        category_code: str,
        unified_name: Optional[str] = None,
        billing_unit: str = "",
    ) -> bool:
        """添加自定义产品映射"""
        if category_code not in self.CATEGORIES:
            logger.error(f"Invalid category code: {category_code}")
            return False

        category = self.CATEGORIES[category_code]
        if not unified_name:
            unified_name = category.category_name

        self.PRODUCT_MAPPING.setdefault(provider, {})[service_name] = (
            category_code,
            unified_name,
            billing_unit,
        )
        self._reverse_map[(provider, service_name)] = {
            "category_code": category_code,
            "unified_name": unified_name,
            "billing_unit": billing_unit,
            "category": category,
        }
        logger.info(f"Added custom mapping: {provider}/{service_name} -> {unified_name}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取映射统计信息"""
        stats = {
            "total_categories": len(self.CATEGORIES),
            "total_mappings": len(self._reverse_map),
            "by_provider": {},
        }
        for provider in self.PRODUCT_MAPPING.keys():
            stats["by_provider"][provider] = len(self.PRODUCT_MAPPING[provider])
        return stats

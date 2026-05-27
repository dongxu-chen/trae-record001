#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目验证脚本 - 检查项目结构和配置是否正确
"""

import os
import sys
import yaml
import json

def check_project_structure():
    print("=" * 60)
    print("Kafka集群巡检工具 - 项目验证")
    print("=" * 60)
    
    required_files = [
        'main.py',
        'config.yaml',
        'requirements.txt',
        'docker-compose.yml',
        'README.md',
        'kafka_inspector/__init__.py',
        'kafka_inspector/kafka_admin_check.py',
        'kafka_inspector/jmx_collector.py',
        'kafka_inspector/prometheus_collector.py',
        'kafka_inspector/bottleneck_analyzer.py',
        'kafka_inspector/partition_advisor.py',
        'kafka_inspector/report_generator.py',
        'prometheus/prometheus.yml',
        'grafana/dashboards/kafka-overview.json',
        'grafana/provisioning/datasources/prometheus.yml',
        'grafana/provisioning/dashboards/kafka.yml',
    ]
    
    print("\n📁 检查项目文件...")
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 缺失")
            all_exist = False
    
    return all_exist

def check_config():
    print("\n⚙️  检查配置文件...")
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['kafka', 'jmx', 'prometheus', 'checks', 'output', 'logging']
        for section in required_sections:
            if section in config:
                print(f"  ✅ 配置段: {section}")
            else:
                print(f"  ❌ 配置段缺失: {section}")
                return False
        
        print(f"  ✅ Kafka集群: {config['kafka']['bootstrap_servers']}")
        print(f"  ✅ JMX主机数: {len(config['jmx']['jmx_hosts'])}")
        print(f"  ✅ Prometheus: {config['prometheus']['url']}")
        print(f"  ✅ 报告格式: {', '.join(config['output']['format'])}")
        print(f"  ✅ 报告目录: {config['output']['report_dir']}")
        
        return True
    except Exception as e:
        print(f"  ❌ 配置文件错误: {str(e)}")
        return False

def check_grafana_dashboard():
    print("\n📊 检查Grafana仪表板...")
    try:
        with open('grafana/dashboards/kafka-overview.json', 'r', encoding='utf-8') as f:
            dashboard = json.load(f)
        
        print(f"  ✅ 仪表板标题: {dashboard.get('title')}")
        print(f"  ✅ 面板数量: {len(dashboard.get('panels', []))}")
        print(f"  ✅ 数据源: Prometheus")
        print(f"  ✅ 刷新间隔: {dashboard.get('refresh')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 仪表板文件错误: {str(e)}")
        return False

def check_docker_compose():
    print("\n🐳 检查Docker Compose配置...")
    try:
        with open('docker-compose.yml', 'r', encoding='utf-8') as f:
            compose = yaml.safe_load(f)
        
        services = compose.get('services', {})
        print(f"  ✅ 服务数量: {len(services)}")
        for service_name in services.keys():
            print(f"     - {service_name}")
        
        return True
    except Exception as e:
        print(f"  ❌ Docker Compose文件错误: {str(e)}")
        return False

def check_requirements():
    print("\n📦 检查依赖清单...")
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"  ✅ 依赖包数量: {len(requirements)}")
        for req in requirements[:5]:
            print(f"     - {req}")
        if len(requirements) > 5:
            print(f"     ... 还有 {len(requirements) - 5} 个")
        
        return True
    except Exception as e:
        print(f"  ❌ 依赖清单错误: {str(e)}")
        return False

def main():
    results = []
    
    results.append(check_project_structure())
    results.append(check_config())
    results.append(check_grafana_dashboard())
    results.append(check_docker_compose())
    results.append(check_requirements())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ 项目验证通过！所有文件和配置都已就绪。")
        print("\n📖 下一步操作:")
        print("  1. 安装依赖: pip install -r requirements.txt")
        print("  2. 启动监控栈: docker-compose up -d")
        print("  3. 执行巡检: python main.py")
        print("  4. 查看报告: 打开 reports/ 目录下的报告文件")
        print("  5. Grafana: http://localhost:3000 (admin/admin)")
    else:
        print("❌ 项目验证失败，请检查上述错误。")
        sys.exit(1)
    print("=" * 60)

if __name__ == '__main__':
    main()

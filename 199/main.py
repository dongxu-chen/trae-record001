import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import time
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from config import KAFKA_CONFIG, KAFKA_TOPICS
from kafka import LiveDataProducer
from flink import StreamProcessingJob
from websocket import WebSocketServer
from suggestion import LiveAdvisor


def create_kafka_topics():
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            client_id='live-dashboard-admin'
        )

        topics = []
        for topic_name in KAFKA_TOPICS.values():
            topics.append(NewTopic(
                name=topic_name,
                num_partitions=1,
                replication_factor=1
            ))

        try:
            admin_client.create_topics(new_topics=topics, validate_only=False)
            print(f"成功创建Kafka Topics: {list(KAFKA_TOPICS.values())}")
        except TopicAlreadyExistsError:
            print(f"Kafka Topics已存在: {list(KAFKA_TOPICS.values())}")

        admin_client.close()
        return True
    except Exception as e:
        print(f"创建Kafka Topics失败: {e}")
        print("请确保Kafka已启动并正确配置")
        return False


def run_producer():
    print("=" * 60)
    print("启动 Kafka 数据生产者")
    print("=" * 60)
    create_kafka_topics()
    producer = LiveDataProducer()
    producer.start()
    producer.wait()


def run_stream_job():
    print("=" * 60)
    print("启动 Flink 流处理作业")
    print("=" * 60)
    create_kafka_topics()
    job = StreamProcessingJob(use_pyflink=False)
    job.register_callback(lambda data: print(
        f"[{time.strftime('%H:%M:%S')}] "
        f"在线:{data['metrics']['current_online']:>5} "
        f"点赞:{data['metrics']['total_likes']:>8} "
        f"成交:¥{data['metrics']['total_amount']:>10,.0f} "
        f"转化:{data['metrics']['conversion_rate']*100:>5.2f}%"
    ))
    job.start()
    job.wait()


def run_websocket_server():
    print("=" * 60)
    print("启动 WebSocket 服务器")
    print("=" * 60)
    create_kafka_topics()

    stream_job = StreamProcessingJob(use_pyflink=False)
    advisor = LiveAdvisor()
    server = WebSocketServer(stream_job, advisor)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


def run_all():
    print("=" * 60)
    print("启动完整直播数据大屏系统")
    print("=" * 60)

    if not create_kafka_topics():
        print("无法连接Kafka，请检查服务状态")
        return

    print("\n正在启动所有组件...\n")

    import subprocess
    import signal

    processes = []

    try:
        print("[1/3] 启动 Kafka 数据生产者...")
        p_producer = subprocess.Popen(
            [sys.executable, 'main.py', 'producer'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(('producer', p_producer))
        time.sleep(2)

        print("[2/3] 启动 WebSocket + Flink 处理服务...")
        p_server = subprocess.Popen(
            [sys.executable, 'main.py', 'server'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(('server', p_server))
        time.sleep(2)

        print("[3/3] 系统启动完成！")
        print("\n" + "=" * 60)
        print("访问数据大屏:")
        print(f"  直接打开: {os.path.join(os.path.abspath('.'), 'frontend', 'index.html')}")
        print("=" * 60)
        print("\n按 Ctrl+C 停止所有服务\n")

        def print_output(name, process):
            try:
                for line in iter(process.stdout.readline, b''):
                    if line:
                        print(f"[{name}] {line.decode('utf-8', errors='ignore').rstrip()}")
            except:
                pass

        import threading
        threads = []
        for name, p in processes:
            t = threading.Thread(target=print_output, args=(name, p), daemon=True)
            t.start()
            threads.append(t)

        while True:
            for name, p in processes:
                if p.poll() is not None:
                    print(f"\n[ERROR] {name} 进程已退出，状态码: {p.returncode}")
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n正在停止所有服务...")
        for name, p in processes:
            try:
                print(f"停止 {name}...")
                p.terminate()
                p.wait(timeout=5)
            except:
                p.kill()
        print("所有服务已停止")


def main():
    parser = argparse.ArgumentParser(
        description='电商直播数据大屏系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py producer     # 启动Kafka数据生产者（模拟直播数据）
  python main.py stream       # 启动Flink流处理作业
  python main.py server       # 启动WebSocket服务器 + 流处理 + 话术建议
  python main.py all          # 启动所有组件
        """
    )
    parser.add_argument(
        'mode',
        nargs='?',
        default='all',
        choices=['producer', 'stream', 'server', 'all'],
        help='运行模式 (默认: all)'
    )

    args = parser.parse_args()

    modes = {
        'producer': run_producer,
        'stream': run_stream_job,
        'server': run_websocket_server,
        'all': run_all,
    }

    modes[args.mode]()


if __name__ == '__main__':
    main()

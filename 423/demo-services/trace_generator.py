"""
演示服务 - 生成模拟Trace数据
用于在没有真实微服务环境时演示拓扑分析功能
"""
import requests
import time
import random
import json
from datetime import datetime, timedelta


class DemoTraceGenerator:
    def __init__(self, jaeger_collector="http://localhost:14268/api/traces"):
        self.collector = jaeger_collector
        self.services = {
            "api-gateway": {"type": "gateway", "port": 8001},
            "user-service": {"type": "service", "port": 8002},
            "order-service": {"type": "service", "port": 8003},
            "payment-service": {"type": "service", "port": 8004},
            "inventory-service": {"type": "service", "port": 8005},
            "notification-service": {"type": "service", "port": 8006},
            "auth-service": {"type": "service", "port": 8007},
            "mysql-db": {"type": "database", "port": 3306},
            "redis-cache": {"type": "cache", "port": 6379},
            "kafka-queue": {"type": "message-queue", "port": 9092},
        }

    def generate_trace_id(self):
        return "".join([format(random.randint(0, 255), "02x") for _ in range(16)])

    def generate_span_id(self):
        return "".join([format(random.randint(0, 255), "02x") for _ in range(8)])

    def create_span(self, trace_id, span_id, parent_span_id, operation_name,
                    service_name, duration, error=False, tags=None, logs=None):
        return {
            "traceID": trace_id,
            "spanID": span_id,
            "operationName": operation_name,
            "references": (
                [{"refType": "CHILD_OF", "traceID": trace_id, "spanID": parent_span_id}]
                if parent_span_id else []
            ),
            "startTime": int(time.time() * 1000000),
            "duration": duration,
            "tags": [
                {"key": "service.name", "type": "string", "value": service_name},
                {"key": "error", "type": "bool", "value": error},
            ] + (tags or []),
            "logs": logs or [],
            "processID": service_name,
        }

    def generate_user_login_trace(self):
        trace_id = self.generate_trace_id()
        spans = []
        now = int(time.time() * 1000000)

        gateway_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, gateway_span_id, None,
            "POST /api/login", "api-gateway",
            random.randint(20000, 50000),
            error=random.random() < 0.02
        ))

        auth_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, auth_span_id, gateway_span_id,
            "AuthenticateUser", "auth-service",
            random.randint(5000, 15000),
            error=random.random() < 0.03
        ))

        redis_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, redis_span_id, auth_span_id,
            "GET session:*", "redis-cache",
            random.randint(1000, 3000)
        ))

        mysql_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, mysql_span_id, auth_span_id,
            "SELECT FROM users", "mysql-db",
            random.randint(2000, 8000),
            error=random.random() < 0.01
        ))

        return self.build_trace(trace_id, spans)

    def generate_create_order_trace(self):
        trace_id = self.generate_trace_id()
        spans = []

        gateway_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, gateway_span_id, None,
            "POST /api/orders", "api-gateway",
            random.randint(50000, 120000),
            error=random.random() < 0.03
        ))

        order_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, order_span_id, gateway_span_id,
            "CreateOrder", "order-service",
            random.randint(30000, 80000),
            error=random.random() < 0.05
        ))

        inventory_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, inventory_span_id, order_span_id,
            "CheckInventory", "inventory-service",
            random.randint(10000, 25000),
            error=random.random() < 0.04
        ))

        mysql_span_id_1 = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, mysql_span_id_1, inventory_span_id,
            "SELECT FROM inventory", "mysql-db",
            random.randint(3000, 10000)
        ))

        payment_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, payment_span_id, order_span_id,
            "ProcessPayment", "payment-service",
            random.randint(20000, 50000),
            error=random.random() < 0.06
        ))

        mysql_span_id_2 = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, mysql_span_id_2, payment_span_id,
            "INSERT INTO transactions", "mysql-db",
            random.randint(5000, 15000)
        ))

        kafka_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, kafka_span_id, order_span_id,
            "Publish OrderCreated", "kafka-queue",
            random.randint(2000, 5000)
        ))

        notification_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, notification_span_id, order_span_id,
            "SendConfirmation", "notification-service",
            random.randint(15000, 35000),
            error=random.random() < 0.02
        ))

        return self.build_trace(trace_id, spans)

    def generate_get_user_trace(self):
        trace_id = self.generate_trace_id()
        spans = []

        gateway_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, gateway_span_id, None,
            "GET /api/users/:id", "api-gateway",
            random.randint(15000, 35000)
        ))

        user_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, user_span_id, gateway_span_id,
            "GetUserProfile", "user-service",
            random.randint(8000, 20000),
            error=random.random() < 0.02
        ))

        redis_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, redis_span_id, user_span_id,
            "GET user:*", "redis-cache",
            random.randint(500, 2000)
        ))

        if random.random() < 0.3:
            mysql_span_id = self.generate_span_id()
            spans.append(self.create_span(
                trace_id, mysql_span_id, user_span_id,
                "SELECT FROM users", "mysql-db",
                random.randint(3000, 8000)
            ))

        return self.build_trace(trace_id, spans)

    def generate_payment_callback_trace(self):
        trace_id = self.generate_trace_id()
        spans = []

        payment_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, payment_span_id, None,
            "PaymentCallback", "payment-service",
            random.randint(25000, 60000),
            error=random.random() < 0.04
        ))

        order_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, order_span_id, payment_span_id,
            "UpdateOrderStatus", "order-service",
            random.randint(10000, 25000)
        ))

        kafka_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, kafka_span_id, order_span_id,
            "Publish OrderPaid", "kafka-queue",
            random.randint(2000, 5000)
        ))

        notification_span_id = self.generate_span_id()
        spans.append(self.create_span(
            trace_id, notification_span_id, order_span_id,
            "SendPaymentSuccessEmail", "notification-service",
            random.randint(10000, 25000)
        ))

        return self.build_trace(trace_id, spans)

    def build_trace(self, trace_id, spans):
        processes = {}
        for span in spans:
            service = span["processID"]
            if service not in processes:
                processes[service] = {
                    "serviceName": service,
                    "tags": [
                        {"key": "service.type", "type": "string",
                         "value": self.services.get(service, {}).get("type", "unknown")},
                    ]
                }

        return {
            "traceID": trace_id,
            "spans": spans,
            "processes": processes,
            "warnings": None,
        }

    def send_trace(self, trace_data):
        try:
            resp = requests.post(
                self.collector,
                json=trace_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            return resp.status_code == 202
        except Exception as e:
            print(f"发送Trace失败: {e}")
            return False

    def generate_demo_traces(self, count=50):
        generators = [
            self.generate_user_login_trace,
            self.generate_create_order_trace,
            self.generate_get_user_trace,
            self.generate_payment_callback_trace,
        ]

        weights = [0.3, 0.35, 0.25, 0.1]
        success_count = 0

        for i in range(count):
            generator = random.choices(generators, weights=weights)[0]
            trace = generator()
            if self.send_trace(trace):
                success_count += 1
            time.sleep(random.uniform(0.05, 0.2))

            if (i + 1) % 10 == 0:
                print(f"已发送 {i + 1}/{count} 条Trace (成功: {success_count})")

        print(f"完成! 发送 {count} 条Trace, 成功 {success_count} 条")
        return success_count


def run_demo():
    generator = DemoTraceGenerator()
    print("=" * 50)
    print("服务拓扑演示 - 生成模拟Trace数据")
    print("=" * 50)

    print("\n[1/3] 生成基础调用链 (100条)...")
    generator.generate_demo_traces(100)

    print("\n[2/3] 生成高负载场景 (200条)...")
    generator.generate_demo_traces(200)

    print("\n[3/3] 生成高错误场景 (50条, 模拟故障)...")
    for i in range(50):
        trace = generator.generate_create_order_trace()
        for span in trace["spans"]:
            if span["operationName"] == "ProcessPayment":
                span["tags"].append({"key": "error", "type": "bool", "value": True})
                span["logs"] = [{
                    "timestamp": int(time.time() * 1000000),
                    "fields": [{"key": "error", "type": "string",
                                "value": "Payment gateway timeout"}]
                }]
        generator.send_trace(trace)
        time.sleep(0.1)

    print("\n" + "=" * 50)
    print("演示数据生成完成!")
    print("请访问 http://localhost:5000 查看拓扑分析")
    print("=" * 50)


if __name__ == "__main__":
    run_demo()

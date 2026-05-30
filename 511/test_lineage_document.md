# 测试血缘文档

**生成时间**: 2026-05-28T02:13:52.045040

## 概览

| 指标 | 数值 |
|------|------|
| 总表数 | 2 |
| 总字段数 | 20 |
| 源表数 | 0 |
| 目标表数 | 1 |
| 表血缘关系 | 1 |
| 字段血缘关系 | 16 |

## 数据字典

### analytics.customer_summary

- **类型**: target
- **源表**: cte3

| 字段名 | 源字段 | 转换逻辑 |
|--------|--------|----------|
| customer_id | cte3.customer_id | - |
| customer_name | cte3.customer_name | - |
| total_orders | cte3.total_orders | - |
| total_amount | cte3.total_amount | - |

### cte3

- **类型**: cte
- **下游表**: analytics.customer_summary

| 字段名 | 源字段 | 转换逻辑 |
|--------|--------|----------|
| customer_id | cte2.c2_id | - |
| customer_name | cte2.c2_name | - |
| total_orders | cte2.order_id | - |
| total_amount | cte2.order_amount | - |

## 关键字段映射

### cte1.c1_id
- **映射链**: c1_id → customer_id → c2_id → c1_id → c1_id → customer_id
- **深度**: 5 层

### cte2.c2_id
- **映射链**: c2_id → customer_id → c2_id → c1_id → c1_id
- **深度**: 4 层

### cte1.c1_name
- **映射链**: c1_name → customer_name → c2_name → c1_name → c1_name → customer_name
- **深度**: 5 层

### cte2.c2_name
- **映射链**: c2_name → customer_name → c2_name → c1_name → c1_name
- **深度**: 4 层

### cte2.order_id
- **映射链**: order_id → total_orders → order_id → order_id
- **深度**: 3 层

### cte2.order_amount
- **映射链**: order_amount → total_amount → order_amount → order_amount
- **深度**: 3 层

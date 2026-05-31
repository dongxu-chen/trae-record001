import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Progress } from 'antd';
import {
  ArrowUpOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useAppStore } from '@/store/appStore';

const Dashboard: React.FC = () => {
  const { dashboardStats, tasks, fetchDashboardStats, fetchTasks } = useAppStore();
  const [trendData, setTrendData] = useState<any>({
    dates: ['01-01', '01-02', '01-03', '01-04', '01-05', '01-06', '01-07'],
    completed: [12, 19, 15, 25, 22, 30, 28],
    failed: [1, 2, 0, 1, 0, 2, 1],
  });

  useEffect(() => {
    fetchDashboardStats();
    fetchTasks();
  }, [fetchDashboardStats, fetchTasks]);

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          running: { color: 'processing', text: '运行中' },
          completed: { color: 'success', text: '已完成' },
          pending: { color: 'default', text: '等待中' },
          failed: { color: 'error', text: '失败' },
          paused: { color: 'warning', text: '已暂停' },
        };
        const cfg = statusMap[status] || statusMap.pending;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (_: any, record: any) => {
        const percent = record.status === 'completed' ? 100 : record.status === 'running' ? 65 : 0;
        return (
          <Progress percent={percent} size="small" status={record.status === 'failed' ? 'exception' : undefined} />
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ];

  const trendChartOption = {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: ['成功', '失败'],
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendData.dates,
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '成功',
        type: 'line',
        smooth: true,
        data: trendData.completed,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.5)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
            ],
          },
        },
      },
      {
        name: '失败',
        type: 'line',
        smooth: true,
        data: trendData.failed,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 77, 79, 0.5)' },
              { offset: 1, color: 'rgba(255, 77, 79, 0.05)' },
            ],
          },
        },
      },
    ],
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">数据概览</h1>

      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={dashboardStats.total || 0}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={dashboardStats.running || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={dashboardStats.completed || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={dashboardStats.failed || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={16}>
          <Card title="执行趋势" className="mb-6">
            <ReactECharts option={trendChartOption} style={{ height: 350 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="任务状态分布">
            <ReactECharts
              option={{
                tooltip: {
                  trigger: 'item',
                },
                legend: {
                  orient: 'vertical',
                  left: 'left',
                },
                series: [
                  {
                    name: '任务状态',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    itemStyle: {
                      borderRadius: 10,
                      borderColor: '#fff',
                      borderWidth: 2,
                    },
                    label: {
                      show: false,
                      position: 'center',
                    },
                    emphasis: {
                      label: {
                        show: true,
                        fontSize: 20,
                        fontWeight: 'bold',
                      },
                    },
                    labelLine: {
                      show: false,
                    },
                    data: [
                      { value: dashboardStats.completed || 8, name: '已完成', itemStyle: { color: '#52c41a' } },
                      { value: dashboardStats.running || 3, name: '运行中', itemStyle: { color: '#1890ff' } },
                      { value: dashboardStats.failed || 1, name: '失败', itemStyle: { color: '#ff4d4f' } },
                    ],
                  },
                ],
              }}
              style={{ height: 350 }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近任务" className="mt-6">
        <Table columns={taskColumns} dataSource={tasks} rowKey="id" pagination={false} />
      </Card>
    </div>
  );
};

export default Dashboard;

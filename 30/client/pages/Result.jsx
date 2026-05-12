import React, { useState, useEffect } from 'react';
import {
  Card,
  Descriptions,
  Progress,
  Tag,
  Space,
  Button,
  message,
  Typography,
  Divider,
  Collapse,
  Empty,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { CollapseProps } from 'antd';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

const API_BASE = 'http://localhost:5000/api/exam';

export default function Result({ resultId, onBack }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await fetch(`${API_BASE}/result/${resultId}`);
        if (!response.ok) throw new Error('获取结果失败');
        const data = await response.json();
        setResult(data);
      } catch (error) {
        message.error('加载考试结果失败');
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [resultId]);

  const getPassedTag = (passed) => {
    if (passed) {
      return <Tag icon={<CheckCircleOutlined />} color="success">通过</Tag>;
    }
    return <Tag icon={<CloseCircleOutlined />} color="error">未通过</Tag>;
  };

  const getScoreStatus = (score) => {
    if (score >= 90) return 'success';
    if (score >= 60) return 'normal';
    return 'exception';
  };

  if (loading) {
    return (
      <Card loading={true} style={{ maxWidth: 900, margin: '20px auto' }}>
        加载中...
      </Card>
    );
  }

  if (!result) {
    return (
      <Card style={{ maxWidth: 900, margin: '20px auto' }}>
      </Card>
    );
  }

  const getCorrectCount = result.answers.filter(a => a.isCorrect).length;
  const wrongCount = result.total_questions - getCorrectCount;

  const panelItems = result.answers.map((answer, index) => ({
    key: String(index + 1),
    label: (
      <Space>
        <span>第 {index + 1} 题</span>
        {answer.isCorrect ? (
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        ) : (
          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
        )}
      </Space>
    ),
    children: (
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Paragraph style={{ fontSize: 15 }}>
          <Text strong>题目：{answer.questionText}</Text>
        </Paragraph>

        <Space direction="vertical" style={{ width: '100%' }}>
          {Object.entries(answer.options).map(([key, value]) => {
            const isCorrect = key === answer.correctAnswer;
            const isUserAnswer = key === answer.userAnswer;
            let color = '';
            let icon = null;

            if (isCorrect) {
              color = '#52c41a';
              icon = <CheckCircleOutlined />;
            } else if (isUserAnswer && !isCorrect) {
              color = '#ff4d4f';
              icon = <CloseCircleOutlined />;
            }

            return (
              <div key={key} style={{ color }}>
                <Space>
                  {icon}
                  <Text strong style={{ color }}>
                    {key}.
                  </Text>
                  <Text style={{ color }}>{value}</Text>
                </Space>
              </div>
            );
          })}
        </Space>

        <Divider style={{ margin: '12px 0' }} />

        <Space>
          <Text type={answer.isCorrect ? 'success' : 'danger'}>
            {answer.isCorrect
              ? `您的答案正确：${answer.userAnswer}，回答正确！`
              : `您的答案：${answer.userAnswer}，正确答案：${answer.correctAnswer}`
            }
          </Text>
        </Space>
      </Space>
    ),
  }));

  return (
    <div style={{ maxWidth: 900, margin: '20px auto', padding: '0 16px' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ textAlign: 'center' }}>
            <Title level={3} style={{ marginBottom: 8 }}>
              考试成绩
            </Title>
            {getPassedTag(result.passed)}
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
            <Progress
              type="circle"
              percent={result.score}
              status={getScoreStatus(result.score)}
              width={140}
              format={percent => `${percent}分`}
            />
          </div>

          <Descriptions bordered column={2}>
            <Descriptions.Item label="考试名称" span={2}>
              {result.exam_title}
            </Descriptions.Item>
            <Descriptions.Item label="考生姓名">
              {result.student_name}
            </Descriptions.Item>
            <Descriptions.Item label="总分">
              {result.score} 分
            </Descriptions.Item>
            <Descriptions.Item label="题目总数">
              {result.total_questions} 题
            </Descriptions.Item>
            <Descriptions.Item label="正确题数">
              <Text type="success">{getCorrectCount} 题</Text>
            </Descriptions.Item>
            <Descriptions.Item label="错误题数">
              <Text type="danger">{wrongCount} 题</Text>
            </Descriptions.Item>
            <Descriptions.Item label="考试时间">
              {new Date(result.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="是否通过">
              {getPassedTag(result.passed)}
            </Descriptions.Item>
          </Descriptions>

          <Divider>
            <ExclamationCircleOutlined /> 答题详情
          </Divider>

          {result.answers.length > 0 ? (
            <Collapse defaultActiveKey={['1']}>
              {panelItems.map(item => (
                <Panel key={item.key} header={item.label}>
                  {item.children}
                </Panel>
              ))}
            </Collapse>
          ) : (
            <Empty description="暂无答题记录" />
          )}

          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={onBack}
            >
              返回首页
            </Button>
          </div>
        </Space>
      </Card>
    </div>
  );
}

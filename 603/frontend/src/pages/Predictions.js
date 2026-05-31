import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Box,
  LinearProgress,
} from '@mui/material';
import { TrendingUp, TrendingDown, Warning } from '@mui/icons-material';
import { getTopics, getPrediction } from '../services/api';

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function Predictions() {
  const [topics, setTopics] = useState([]);
  const [predictions, setPredictions] = useState({});

  const fetchData = async () => {
    try {
      const topicsRes = await getTopics();
      const topicList = topicsRes.data.topics || [];
      setTopics(topicList);

      const preds = {};
      for (const topic of topicList) {
        try {
          const res = await getPrediction(topic);
          preds[topic] = res.data;
        } catch (e) {
          preds[topic] = null;
        }
      }
      setPredictions(preds);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getRiskLevel = (prediction) => {
    if (!prediction) return { level: '未知', color: 'default', icon: null };
    const byteBacklog = prediction.PredictedByteBacklog || 0;
    const msgBacklog = prediction.PredictedBacklog || 0;
    const effectiveVal = byteBacklog > 0 ? byteBacklog : msgBacklog;
    if (effectiveVal > 100000) {
      return { level: '高危', color: 'error', icon: <Warning /> };
    }
    if (effectiveVal > 50000) {
      return { level: '中风险', color: 'warning', icon: <TrendingUp /> };
    }
    return { level: '正常', color: 'success', icon: <TrendingDown /> };
  };

  const totalPredicted = Object.values(predictions).reduce(
    (sum, p) => sum + (p?.PredictedBacklog || 0),
    0
  );
  const totalPredictedBytes = Object.values(predictions).reduce(
    (sum, p) => sum + (p?.PredictedByteBacklog || 0),
    0
  );
  const highRiskCount = Object.values(predictions).filter(
    (p) => {
      const val = p?.PredictedByteBacklog || p?.PredictedBacklog || 0;
      return val > 50000;
    }
  ).length;

  return (
    <div>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">积压预测</Typography>
        <Typography variant="body2" color="textSecondary">
          线性回归 + 消息大小因子 (预测1小时后积压)
        </Typography>
      </Box>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>监控 Topic 数</Typography>
              <Typography variant="h4">{topics.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>预测消息积压</Typography>
              <Typography variant="h4">{totalPredicted.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>预测字节积压</Typography>
              <Typography variant="h4">{formatBytes(totalPredictedBytes)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>高风险 Topic</Typography>
              <Typography variant="h4" color={highRiskCount > 0 ? 'error' : 'success'}>
                {highRiskCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Topic</TableCell>
              <TableCell align="right">预测消息积压</TableCell>
              <TableCell align="right">预测字节积压</TableCell>
              <TableCell align="right">消息大小因子</TableCell>
              <TableCell align="right">置信度</TableCell>
              <TableCell align="center">风险等级</TableCell>
              <TableCell>预测时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topics.map((topic) => {
              const prediction = predictions[topic];
              const risk = getRiskLevel(prediction);
              return (
                <TableRow key={topic}>
                  <TableCell component="th" scope="row">{topic}</TableCell>
                  <TableCell align="right">
                    {prediction ? prediction.PredictedBacklog?.toLocaleString() : '暂无数据'}
                  </TableCell>
                  <TableCell align="right">
                    {prediction ? formatBytes(prediction.PredictedByteBacklog) : '-'}
                  </TableCell>
                  <TableCell align="right">
                    {prediction ? (
                      <Chip
                        label={`${(prediction.MsgSizeFactor || 1).toFixed(2)}x`}
                        size="small"
                        color={prediction.MsgSizeFactor > 5 ? 'error' : prediction.MsgSizeFactor > 2 ? 'warning' : 'success'}
                      />
                    ) : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ width: 160 }}>
                    {prediction ? (
                      <Box display="flex" alignItems="center">
                        <Box width="100%" mr={1}>
                          <LinearProgress
                            variant="determinate"
                            value={(prediction.Confidence || 0) * 100}
                            color={prediction.Confidence > 0.7 ? 'success' : 'warning'}
                          />
                        </Box>
                        <Box minWidth={35}>
                          <Typography variant="body2" color="textSecondary">
                            {`${Math.round((prediction.Confidence || 0) * 100)}%`}
                          </Typography>
                        </Box>
                      </Box>
                    ) : '-'}
                  </TableCell>
                  <TableCell align="center">
                    <Chip icon={risk.icon} label={risk.level} color={risk.color} size="small" />
                  </TableCell>
                  <TableCell>
                    {prediction ? new Date(prediction.PredictedTime).toLocaleString() : '-'}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>预测模型说明</Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            本系统使用线性回归算法对消息积压进行预测，并引入消息大小因子修正评估：
          </Typography>
          <ul>
            <li>
              <Typography variant="body2">
                <strong>数据来源：</strong>使用过去24小时的积压历史数据（含消息大小信息）
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                <strong>预测算法：</strong>线性回归 + 消息大小因子 (Linear Regression with Size Factor)
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                <strong>消息大小因子：</strong>EffectiveBacklog = BacklogSize × (AvgMsgSize / 1KB)，考虑大消息场景的实际存储压力
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                <strong>双维度评估：</strong>同时预测消息数量积压和字节积压，大消息Topic的告警更准确
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                <strong>预测范围：</strong>预测未来1小时的积压趋势
              </Typography>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export default Predictions;

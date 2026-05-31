import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  Divider,
  Grid,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';

function JudgmentPrediction({ prediction }) {
  if (!prediction) return null;

  const {
    predicted_outcome,
    outcome_probabilities,
    amount_prediction,
    key_determinants,
    confidence,
    reasoning,
    partial_support_risks,
    reference_case_count,
  } = prediction;

  const getOutcomeColor = (outcome) => {
    if (outcome.includes('全部支持')) return 'success';
    if (outcome.includes('部分支持')) return 'warning';
    if (outcome.includes('驳回')) return 'error';
    return 'default';
  };

  const getConfidenceLevel = (conf) => {
    if (conf >= 0.7) return { label: '高', color: 'success' };
    if (conf >= 0.5) return { label: '中', color: 'warning' };
    return { label: '低', color: 'error' };
  };

  const confidenceInfo = getConfidenceLevel(confidence);

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TrendingUpIcon color="primary" />
        判决预测
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Alert
            severity={getOutcomeColor(predicted_outcome)}
            variant="filled"
            sx={{ mb: 2 }}
          >
            <Typography variant="subtitle1" fontWeight="bold">
              预测结果：{predicted_outcome}
            </Typography>
            <Typography variant="body2">
              置信度：{(confidence * 100).toFixed(1)}%（{confidenceInfo.label}）
            </Typography>
          </Alert>

          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            判决概率分布
          </Typography>
          {outcome_probabilities && Object.entries(outcome_probabilities).map(([outcome, prob]) => (
            <Box key={outcome} sx={{ mb: 1.5 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{outcome}</Typography>
                <Typography variant="body2" fontWeight="medium">{(prob * 100).toFixed(1)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={prob * 100}
                color={getOutcomeColor(outcome)}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          ))}
        </Grid>

        <Grid item xs={12} md={6}>
          {amount_prediction && amount_prediction.claimed_amount > 0 && (
            <>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                金额预测
              </Typography>
              <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500 }}>主张金额</TableCell>
                      <TableCell align="right">{amount_prediction.claimed_amount?.toLocaleString()} 元</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500 }}>预测本金支持</TableCell>
                      <TableCell align="right">{amount_prediction.predicted_principal?.toLocaleString()} 元</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500 }}>预测利息支持</TableCell>
                      <TableCell align="right">{amount_prediction.predicted_interest?.toLocaleString()} 元</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500, color: 'primary.main' }}>预测总额</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, color: 'primary.main' }}>
                        {amount_prediction.predicted_total?.toLocaleString()} 元
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500 }}>支持率</TableCell>
                      <TableCell align="right">{(amount_prediction.support_rate * 100).toFixed(1)}%</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </Grid>

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            关键决定因素
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {key_determinants && key_determinants.map((det, idx) => (
              <Chip
                key={idx}
                icon={
                  det.impact === 'positive' ? <CheckCircleIcon /> :
                  det.impact === 'negative' ? <WarningIcon /> : <InfoIcon />
                }
                label={`${det.factor} (${det.impact === 'positive' ? '有利' : det.impact === 'negative' ? '不利' : '待定'})`}
                size="small"
                color={
                  det.impact === 'positive' ? 'success' :
                  det.impact === 'negative' ? 'error' : 'default'
                }
                variant="outlined"
                sx={{ maxWidth: '100%' }}
              />
            ))}
          </Box>
        </Grid>

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            预测分析
          </Typography>
          <List dense disablePadding>
            {reasoning && reasoning.map((r, idx) => (
              <ListItem key={idx} disablePadding sx={{ py: 0.5 }}>
                <ListItemText
                  primary={r}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            ))}
          </List>
        </Grid>

        {partial_support_risks && partial_support_risks.length > 0 && (
          <Grid item xs={12}>
            <Alert severity="warning" sx={{ mt: 1 }}>
              <Typography variant="subtitle2">部分支持风险因素：</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                {partial_support_risks.map((risk, idx) => (
                  <Chip key={idx} label={risk} size="small" color="warning" variant="outlined" />
                ))}
              </Box>
            </Alert>
          </Grid>
        )}

        <Grid item xs={12}>
          <Typography variant="caption" color="text.secondary">
            * 基于 {reference_case_count} 个相似案例统计分析，置信度 {confidenceInfo.label}。判决预测仅供参考，不构成法律意见。
          </Typography>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default JudgmentPrediction;

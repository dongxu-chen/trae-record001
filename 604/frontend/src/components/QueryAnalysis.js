import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  Divider,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import LabelIcon from '@mui/icons-material/Label';
import SummarizeIcon from '@mui/icons-material/Summarize';
import GavelIcon from '@mui/icons-material/Gavel';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

function QueryAnalysis({ analysis }) {
  if (!analysis) return null;

  const { legal_entities, key_points, case_type, summary, keywords, sentencing_factors, sentencing_summary } = analysis;

  const entityLabels = {
    '原告': { color: 'primary', label: '原告' },
    '被告': { color: 'error', label: '被告' },
    '金额': { color: 'success', label: '金额' },
    '日期': { color: 'info', label: '日期' },
    '地点': { color: 'info', label: '地点' },
    '证据': { color: 'warning', label: '证据' },
    '法条': { color: 'secondary', label: '法条' },
    '罪名': { color: 'error', label: '罪名' },
    '法院': { color: 'primary', label: '法院' },
    '诉讼请求': { color: 'secondary', label: '诉讼请求' },
    '量刑建议': { color: 'error', label: '量刑建议' },
  };

  const getSeverityColor = (level) => {
    if (level === '严重' || level === '重大' || level === '故意' || level === '累犯' || level === '无悔罪') return 'error';
    if (level === '一般' || level === '过失') return 'warning';
    if (level === '轻微' || level === '较小' || level === '初犯' || level === '有悔罪') return 'success';
    return 'default';
  };

  const getSeverityLabel = (level) => {
    const map = {
      '严重': '🔴 严重', '一般': '🟡 一般', '轻微': '🟢 轻微',
      '重大': '🔴 重大', '较小': '🟢 较小',
      '故意': '🔴 故意', '过失': '🟡 过失', '间接故意': '🟠 间接故意',
      '有悔罪': '🟢 有悔罪', '无悔罪': '🔴 无悔罪',
      '累犯': '🔴 累犯', '初犯': '🟢 初犯',
      '从重': '🔴 从重', '从轻': '🟢 从轻',
      '法定刑': '⚖️ 法定刑',
      '人身损害': '🔴 人身损害', '财产损害': '🟡 财产损害',
    };
    return map[level] || level;
  };

  const renderSentencingFactors = () => {
    if (!sentencing_factors || Object.keys(sentencing_factors).length === 0) return null;

    return (
      <Grid item xs={12}>
        <Divider sx={{ my: 1 }} />
        <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <GavelIcon fontSize="small" color="secondary" />
          量刑要素标注
        </Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 1 }}>
          <Table size="small">
            <TableBody>
              {Object.entries(sentencing_factors).map(([category, items]) => (
                items.map((item, idx) => (
                  <TableRow key={`${category}-${idx}`}>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 500, width: 120, borderBottom: idx === items.length - 1 && '1px solid rgba(224,224,224,1)' }}>
                      {category}
                    </TableCell>
                    <TableCell sx={{ borderBottom: idx === items.length - 1 && '1px solid rgba(224,224,224,1)' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Chip
                          label={getSeverityLabel(item.level)}
                          size="small"
                          color={getSeverityColor(item.level)}
                          variant="outlined"
                        />
                        {item.keywords && item.keywords.map((kw, kIdx) => (
                          <Chip key={kIdx} label={kw} size="small" variant="filled" color={getSeverityColor(item.level)} />
                        ))}
                        {item.amount && (
                          <Chip label={`${item.amount} (${item.grade})`} size="small" color="primary" />
                        )}
                        {item.value && typeof item.value === 'string' && (
                          <Chip label={`${item.type}: ${item.value}`} size="small" variant="outlined" />
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Grid>
    );
  };

  const renderSentencingSummary = () => {
    if (!sentencing_summary) return null;

    const severityColor = sentencing_summary.severity_assessment === '严重' ? 'error' :
                          sentencing_summary.severity_assessment === '轻微' ? 'success' : 'warning';

    return (
      <Grid item xs={12}>
        <Divider sx={{ my: 1 }} />
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          量刑综合评估
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
          <Alert severity={severityColor} icon={<GavelIcon />} sx={{ py: 0 }}>
            严重程度评估：<strong>{sentencing_summary.severity_assessment}</strong>
          </Alert>

          {sentencing_summary.aggravating && sentencing_summary.aggravating.length > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <WarningIcon color="error" fontSize="small" sx={{ mt: 0.5 }} />
              <Box>
                <Typography variant="caption" color="error.main">从重因素</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {sentencing_summary.aggravating.map((f, idx) => (
                    <Chip key={idx} label={f} size="small" color="error" variant="outlined" />
                  ))}
                </Box>
              </Box>
            </Box>
          )}

          {sentencing_summary.mitigating && sentencing_summary.mitigating.length > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <CheckCircleIcon color="success" fontSize="small" sx={{ mt: 0.5 }} />
              <Box>
                <Typography variant="caption" color="success.main">从轻因素</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {sentencing_summary.mitigating.map((f, idx) => (
                    <Chip key={idx} label={f} size="small" color="success" variant="outlined" />
                  ))}
                </Box>
              </Box>
            </Box>
          )}
        </Box>
      </Grid>
    );
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <SummarizeIcon color="primary" />
        案情分析结果
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AccountBalanceIcon fontSize="small" />
              案件类型
            </Typography>
            <Chip label={case_type || '未识别'} color="primary" variant="outlined" />
          </Box>
        </Grid>

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            案情摘要（TextRank抽取式）
          </Typography>
          <Typography variant="body1" paragraph>
            {summary}
          </Typography>
        </Grid>

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <LabelIcon fontSize="small" />
            法律实体识别
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {Object.entries(legal_entities).map(([type, entities]) => (
              entities && entities.length > 0 && (
                <Box key={type} sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
                    {entityLabels[type]?.label || type}：
                  </Typography>
                  {entities.map((entity, idx) => (
                    <Chip
                      key={idx}
                      label={entity}
                      size="small"
                      color={entityLabels[type]?.color || 'default'}
                      variant="outlined"
                    />
                  ))}
                </Box>
              )
            ))}
          </Box>
        </Grid>

        {renderSentencingFactors()}
        {renderSentencingSummary()}

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            裁判要点（抽取式摘要）
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {key_points && key_points.map((point, idx) => (
              <Box key={idx} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                <Chip label={idx + 1} size="small" color="primary" sx={{ minWidth: 28 }} />
                <Typography variant="body2">{point}</Typography>
              </Box>
            ))}
          </Box>
        </Grid>

        {keywords && keywords.length > 0 && (
          <Grid item xs={12}>
            <Divider sx={{ my: 1 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              关键词
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {keywords.map((keyword, idx) => (
                <Chip key={idx} label={keyword} size="small" variant="outlined" />
              ))}
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
}

export default QueryAnalysis;

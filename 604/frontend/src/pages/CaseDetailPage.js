import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Paper,
  Typography,
  Box,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import DateRangeIcon from '@mui/icons-material/DateRange';
import GavelIcon from '@mui/icons-material/Gavel';
import LabelIcon from '@mui/icons-material/Label';
import DescriptionIcon from '@mui/icons-material/Description';
import SummarizeIcon from '@mui/icons-material/Summarize';

function CaseDetailPage({ apiService }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [caseData, setCaseData] = useState(null);

  useEffect(() => {
    const fetchCaseDetail = async () => {
      try {
        setLoading(true);
        const result = await apiService.getCaseDetail(id);
        if (result.success) {
          setCaseData(result.case);
        } else {
          setError('案例未找到');
        }
      } catch (err) {
        setError('获取案例详情失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCaseDetail();
  }, [id, apiService]);

  const handleBack = () => {
    navigate('/');
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !caseData) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>
          返回搜索
        </Button>
        <Alert severity="error">{error || '案例未找到'}</Alert>
      </Box>
    );
  }

  const entityLabels = {
    '原告': { color: 'primary', label: '原告' },
    '被告': { color: 'error', label: '被告' },
    '金额': { color: 'success', label: '金额' },
    '日期': { color: 'info', label: '日期' },
    '证据': { color: 'warning', label: '证据' },
    '法条': { color: 'secondary', label: '法条' },
  };

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>
        返回搜索
      </Button>

      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 500, mb: 3 }}>
          {caseData.case_title}
        </Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
          <Chip
            icon={<AccountBalanceIcon />}
            label={caseData.court || '未知法院'}
            variant="outlined"
          />
          <Chip
            icon={<DateRangeIcon />}
            label={caseData.judgment_date || '未知日期'}
            variant="outlined"
          />
          <Chip
            icon={<GavelIcon />}
            label={caseData.case_type}
            color="primary"
          />
          <Chip
            label={`案例编号: ${caseData.case_id}`}
            variant="outlined"
          />
        </Box>

        <Divider sx={{ my: 3 }} />

        <Grid container spacing={4}>
          <Grid item xs={12} md={8}>
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <DescriptionIcon color="primary" />
                案情描述
              </Typography>
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {caseData.description}
              </Typography>
            </Box>

            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SummarizeIcon color="primary" />
                案情摘要
              </Typography>
              <Typography variant="body1" sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
                {caseData.summary}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LabelIcon color="primary" />
                法律实体
              </Typography>
              <List dense disablePadding>
                {Object.entries(caseData.legal_entities || {}).map(([type, entities]) => (
                  entities && entities.length > 0 && (
                    <ListItem key={type} disablePadding sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 50 }}>
                        <Typography variant="caption" color="text.secondary">
                          {entityLabels[type]?.label || type}
                        </Typography>
                      </ListItemIcon>
                      <ListItemText
                        disableTypography
                        primary={
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
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
                        }
                      />
                    </ListItem>
                  )
                ))}
              </List>
            </Box>

            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <GavelIcon color="secondary" />
                裁判要点
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {caseData.key_points && caseData.key_points.map((point, idx) => (
                  <Chip key={idx} label={point} />
                ))}
              </Box>
            </Box>

            {caseData.recommended_laws && caseData.recommended_laws.length > 0 && (
              <Box>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <GavelIcon color="secondary" />
                  相关法条
                </Typography>
                <List dense disablePadding>
                  {caseData.recommended_laws.map((law, idx) => (
                    <ListItem key={idx} alignItems="flex-start">
                      <ListItemText
                        primary={law.law_id}
                        secondary={law.content}
                        primaryTypographyProps={{ fontWeight: 500 }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}

export default CaseDetailPage;

import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import FilterCenterFocusIcon from '@mui/icons-material/FilterCenterFocus';
import ArrowRightIcon from '@mui/icons-material/ArrowRight';
import GavelIcon from '@mui/icons-material/Gavel';
import LightbulbIcon from '@mui/icons-material/Lightbulb';

function DisputeFocusAnalysis({ analysis }) {
  if (!analysis) return null;

  const { dispute_foci, plaintiff_stance, defendant_stance, core_dispute, dispute_chain, resolution_suggestions } = analysis;

  const getCategoryColor = (category) => {
    const map = {
      '事实争议': 'error',
      '法律适用争议': 'primary',
      '程序争议': 'warning',
      '证据争议': 'secondary',
    };
    return map[category] || 'default';
  };

  const getIntensityColor = (intensity) => {
    const map = { '高': 'error', '中': 'warning', '低': 'success' };
    return map[intensity] || 'default';
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <FilterCenterFocusIcon color="primary" />
        争议焦点分析
      </Typography>

      <Grid container spacing={3}>
        {core_dispute && (
          <Grid item xs={12}>
            <Alert
              severity={getIntensityColor(core_dispute.intensity) === 'error' ? 'error' : 'info'}
              variant="filled"
            >
              <Typography variant="subtitle1" fontWeight="bold">
                核心争议：{core_dispute.core_issue}
              </Typography>
              <Typography variant="body2">
                争议类型：{core_dispute.dispute_type} | 争议强度：
                <Chip label={core_dispute.intensity} size="small" color={getIntensityColor(core_dispute.intensity)} sx={{ ml: 1 }} />
              </Typography>
              {core_dispute.description && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {core_dispute.description}
                </Typography>
              )}
            </Alert>
          </Grid>
        )}

        {plaintiff_stance && plaintiff_stance.length > 0 && (
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="primary.main" gutterBottom>
              原告主张
            </Typography>
            <List dense disablePadding>
              {plaintiff_stance.map((stance, idx) => (
                <ListItem key={idx} disablePadding sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 28 }}>
                    <ArrowRightIcon fontSize="small" color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary={stance.content}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </Grid>
        )}

        {defendant_stance && defendant_stance.length > 0 && (
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="error.main" gutterBottom>
              被告主张
            </Typography>
            <List dense disablePadding>
              {defendant_stance.map((stance, idx) => (
                <ListItem key={idx} disablePadding sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 28 }}>
                    <ArrowRightIcon fontSize="small" color="error" />
                  </ListItemIcon>
                  <ListItemText
                    primary={stance.content}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </Grid>
        )}

        <Grid item xs={12}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            争议焦点清单
          </Typography>
          {dispute_foci && dispute_foci.map((focus, idx) => (
            <Accordion key={idx} defaultExpanded={idx === 0}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <Chip
                    label={focus.category}
                    size="small"
                    color={getCategoryColor(focus.category)}
                  />
                  <Typography variant="body2" fontWeight="medium">
                    {focus.focus}
                  </Typography>
                  <Chip
                    label={`重要性 ${(focus.importance * 100).toFixed(0)}%`}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" color="text.secondary">
                  子类：{focus.subcategory}
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                  {focus.matched_keywords && focus.matched_keywords.map((kw, kIdx) => (
                    <Chip key={kIdx} label={kw} size="small" />
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}
        </Grid>

        {dispute_chain && dispute_chain.length > 0 && (
          <Grid item xs={12}>
            <Divider sx={{ my: 1 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <GavelIcon fontSize="small" />
              争议分析链条
            </Typography>
            <Stepper orientation="vertical" nonLinear>
              {dispute_chain.map((step, idx) => (
                <Step key={idx} active={true}>
                  <StepLabel>{step.stage}</StepLabel>
                  <StepContent>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {step.description}
                    </Typography>
                    {step.foci && step.foci.map((f, fIdx) => (
                      <Chip key={fIdx} label={f.focus} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                    ))}
                  </StepContent>
                </Step>
              ))}
            </Stepper>
          </Grid>
        )}

        {resolution_suggestions && resolution_suggestions.length > 0 && (
          <Grid item xs={12}>
            <Divider sx={{ my: 1 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <LightbulbIcon fontSize="small" color="warning" />
              争议解决建议
            </Typography>
            <List dense disablePadding>
              {resolution_suggestions.map((suggestion, idx) => (
                <ListItem key={idx} disablePadding sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 28 }}>
                    <Chip
                      label={suggestion.priority}
                      size="small"
                      color={suggestion.priority === '高' ? 'error' : 'default'}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip label={suggestion.type} size="small" variant="outlined" />
                        <Typography variant="body2">{suggestion.description}</Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
}

export default DisputeFocusAnalysis;

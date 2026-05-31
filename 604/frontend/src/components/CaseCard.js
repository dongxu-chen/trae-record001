import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Chip,
  Button,
  Divider,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SimilarityIcon from '@mui/icons-material/Compare';
import DifferenceIcon from '@mui/icons-material/Difference';
import LawIcon from '@mui/icons-material/Gavel';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useNavigate } from 'react-router-dom';

function CaseCard({ caseData, index }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const {
    case_id, case_title, case_type, similarity_score, summary,
    key_points, legal_entities, difference_analysis, recommended_laws
  } = caseData;

  const getSimilarityColor = (score) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'primary';
    if (score >= 0.4) return 'warning';
    return 'error';
  };

  const getSimilarityLabel = (score) => {
    if (score >= 0.8) return '高度相似';
    if (score >= 0.6) return '较为相似';
    if (score >= 0.4) return '部分相似';
    return '差异较大';
  };

  const handleViewDetail = () => {
    navigate(`/case/${case_id}`);
  };

  return (
    <Card sx={{ mb: 2, transition: '0.3s', '&:hover': { boxShadow: 6 } }}>
      <CardContent sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ flex: 1, mr: 2 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
              #{index + 1} {case_title}
            </Typography>
            <Chip label={case_type} size="small" variant="outlined" sx={{ mr: 1 }} />
            <Chip
              icon={<SimilarityIcon />}
              label={`${(similarity_score * 100).toFixed(1)}% - ${getSimilarityLabel(similarity_score)}`}
              size="small"
              color={getSimilarityColor(similarity_score)}
            />
          </Box>
          <Box sx={{ width: 120, textAlign: 'right' }}>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              相似度
            </Typography>
            <LinearProgress
              variant="determinate"
              value={similarity_score * 100}
              color={getSimilarityColor(similarity_score)}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {summary}
        </Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
          {key_points && key_points.slice(0, 5).map((point, idx) => (
            <Chip key={idx} label={point} size="small" />
          ))}
        </Box>
      </CardContent>

      <Accordion expanded={expanded} onChange={() => setExpanded(!expanded)}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="body2">查看详细分析</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <DifferenceIcon fontSize="small" color="primary" />
                差异分析 - ${difference_analysis?.similarity_level || '未知'}
              </Typography>
              <List dense disablePadding>
                {difference_analysis?.key_points?.common?.length > 0 && (
                  <ListItem>
                    <ListItemText
                      primary={`共同点: ${difference_analysis.key_points.common.slice(0, 3).join('、')}
                      primaryTypographyProps={{ variant: 'body2', color: 'success.main' }}
                    />
                  </ListItem>
                )}
                {difference_analysis?.key_points?.query_only?.length > 0 && (
                  <ListItem>
                    <ListItemText
                      primary={`本案独有: ${difference_analysis.key_points.query_only.slice(0, 2).join('、')}
                      primaryTypographyProps={{ variant: 'body2', color: 'warning.main' }}
                    />
                  </ListItem>
                )}
                {difference_analysis?.key_points?.case_only?.length > 0 && (
                  <ListItem>
                    <ListItemText
                      primary={`案例独有: ${difference_analysis.key_points.case_only.slice(0, 2).join('、')}
                      primaryTypographyProps={{ variant: 'body2', color: 'info.main' }}
                    />
                  </ListItem>
                )}
              </List>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <LawIcon fontSize="small" color="secondary" />
                推荐法条
              </Typography>
              <List dense disablePadding>
                {recommended_laws && recommended_laws.slice(0, 3).map((law, idx) => (
                  <ListItem key={idx}>
                    <ListItemText
                      primary={law.law_id}
                      secondary={law.content?.slice(0, 50)} + '...'
                      primaryTypographyProps={{ variant: 'body2' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Divider />

      <CardActions>
        <Button
          size="small"
          endIcon={<ArrowForwardIcon />}
          onClick={handleViewDetail}
        >
          查看详情
        </Button>
      </CardActions>
    </Card>
  );
}

export default CaseCard;

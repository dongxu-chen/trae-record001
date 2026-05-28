import React, { useState } from 'react';
import { 
  Box, Typography, List, ListItem, ListItemText, Chip, 
  Button, Divider, Collapse, IconButton, Accordion,
  AccordionSummary, AccordionDetails, Paper, Badge, 
  FormControlLabel, Switch
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import { diffWords } from 'diff';

const AISuggestionPanel = ({ suggestions, summary, onAccept, onReject, onIgnore, onBatchAccept, onBatchIgnore }) => {
  const [expanded, setExpanded] = useState({});
  const [filterType, setFilterType] = useState('all');
  const [showDetails, setShowDetails] = useState(false);

  const filteredSuggestions = suggestions.filter(s => {
    if (filterType === 'all') return true;
    return s.type === filterType;
  });

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'medium':
        return <WarningIcon color="warning" fontSize="small" />;
      default:
        return <InfoIcon color="info" fontSize="small" />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      default:
        return 'info';
    }
  };

  const renderDiff = (original, suggested) => {
    if (!suggested) return <span>{original}</span>;
    
    const diff = diffWords(original, suggested);
    
    return (
      <span>
        {diff.map((part, idx) => (
          <span
            key={idx}
            style={{
              backgroundColor: part.added ? '#d4edda' : part.removed ? '#f8d7da' : 'transparent',
              color: part.added ? '#155724' : part.removed ? '#721c24' : 'inherit',
              textDecoration: part.removed ? 'line-through' : 'none'
            }}
          >
            {part.value}
          </span>
        ))}
      </span>
    );
  };

  const handleToggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const typeLabels = {
    typo: '错别字',
    grammar: '语法',
    style: '风格',
    clarity: '清晰度',
    format: '格式',
    consistency: '一致性'
  };

  return (
    <Paper sx={{ p: 2, bgcolor: '#fafafa' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box display="flex" alignItems="center" gap={1}>
          <AutoAwesomeIcon color="primary" />
          <Typography variant="h6">AI 智能审阅</Typography>
          {summary && (
            <Badge badgeContent={summary.total} color="primary" />
          )}
        </Box>
        <Box display="flex" gap={1}>
          <Button 
            size="small" 
            variant="outlined"
            onClick={() => onBatchAccept(suggestions.filter(s => s.status === 'pending').map(s => s._id))}
            disabled={suggestions.filter(s => s.status === 'pending').length === 0}
          >
            全部接受
          </Button>
          <Button 
            size="small" 
            variant="outlined"
            onClick={() => onBatchIgnore(suggestions.filter(s => s.status === 'pending').map(s => s._id))}
            disabled={suggestions.filter(s => s.status === 'pending').length === 0}
          >
            全部忽略
          </Button>
        </Box>
      </Box>

      {summary && (
        <Box display="flex" gap={2} mb={2} flexWrap="wrap">
          {Object.entries(summary.byType || {}).map(([type, count]) => (
            <Chip 
              key={type}
              label={`${typeLabels[type] || type}: ${count}`}
              size="small"
              variant={filterType === type ? 'filled' : 'outlined'}
              onClick={() => setFilterType(filterType === type ? 'all' : type)}
              sx={{ cursor: 'pointer' }}
            />
          ))}
          <Chip 
            label={`全部: ${summary.total}`}
            size="small"
            variant={filterType === 'all' ? 'filled' : 'outlined'}
            onClick={() => setFilterType('all')}
            sx={{ cursor: 'pointer' }}
          />
        </Box>
      )}

      <FormControlLabel
        control={
          <Switch
            checked={showDetails}
            onChange={(e) => setShowDetails(e.target.checked)}
            size="small"
          />
        }
        label="显示详情"
      />

      <Divider sx={{ my: 2 }} />

      <List sx={{ maxHeight: 400, overflow: 'auto' }}>
        {filteredSuggestions.length === 0 ? (
          <ListItem>
            <ListItemText 
              primary="暂无建议" 
              secondary={filterType !== 'all' ? `没有${typeLabels[filterType]}类型的建议` : '文档质量良好，没有发现问题'}
            />
          </ListItem>
        ) : (
          filteredSuggestions.map((suggestion, index) => (
            <React.Fragment key={suggestion._id || index}>
              <Accordion 
                expanded={expanded[index]}
                onChange={() => handleToggleExpand(index)}
                sx={{ 
                  bgcolor: suggestion.status === 'pending' ? 'white' : 'grey.50',
                  opacity: suggestion.status !== 'pending' ? 0.7 : 1
                }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={1} sx={{ width: '100%' }}>
                    {getSeverityIcon(suggestion.severity)}
                    <Chip 
                      label={typeLabels[suggestion.type] || suggestion.type}
                      size="small"
                      color={getSeverityColor(suggestion.severity)}
                      sx={{ mr: 1 }}
                    />
                    {suggestion.status !== 'pending' && (
                      <Chip 
                        label={suggestion.status === 'accepted' ? '已接受' : '已忽略'}
                        size="small"
                        color={suggestion.status === 'accepted' ? 'success' : 'default'}
                      />
                    )}
                    <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                      {suggestion.explanation}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box mb={2}>
                    <Typography variant="caption" color="text.secondary">原文:</Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {renderDiff(suggestion.originalText, suggestion.suggestedText)}
                    </Typography>
                  </Box>
                  
                  {suggestion.context && showDetails && (
                    <Box mb={2}>
                      <Typography variant="caption" color="text.secondary">上下文:</Typography>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
                        {suggestion.context}
                      </Typography>
                    </Box>
                  )}

                  {showDetails && (
                    <Box display="flex" gap={2} mb={2}>
                      <Typography variant="caption" color="text.secondary">
                        类别: {suggestion.category}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        置信度: {Math.round((suggestion.confidence || 0) * 100)}%
                      </Typography>
                    </Box>
                  )}

                  {suggestion.status === 'pending' && (
                    <Box display="flex" gap={1} mt={2}>
                      <Button
                        size="small"
                        variant="contained"
                        color="success"
                        startIcon={<CheckIcon />}
                        onClick={() => onAccept(suggestion._id)}
                      >
                        接受
                      </Button>
                      <Button
                        size="small"
                        variant="contained"
                        color="error"
                        startIcon={<CloseIcon />}
                        onClick={() => onReject(suggestion._id)}
                      >
                        拒绝
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<VisibilityOffIcon />}
                        onClick={() => onIgnore(suggestion._id)}
                      >
                        忽略
                      </Button>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
              {index < filteredSuggestions.length - 1 && <Divider />}
            </React.Fragment>
          ))
        )}
      </List>
    </Paper>
  );
};

export default AISuggestionPanel;

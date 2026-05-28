import React, { useState } from 'react';
import { 
  Box, Typography, Grid, Paper, Chip, Select, MenuItem, 
  FormControl, InputLabel, Divider
} from '@mui/material';

const SideBySideDiff = ({ revisions, currentContent, currentRichContent }) => {
  const [selectedRevision, setSelectedRevision] = useState(null);

  if (!revisions || revisions.length === 0) {
    return (
      <Box p={3} textAlign="center">
        <Typography color="text.secondary">暂无修订记录可供对比</Typography>
      </Box>
    );
  }

  const getDiffData = () => {
    if (!selectedRevision) {
      return {
        oldContent: currentContent,
        newContent: currentContent,
        oldRich: currentRichContent,
        newRich: currentRichContent
      };
    }

    try {
      const sideBySideDiff = JSON.parse(selectedRevision.sideBySideDiff);
      return {
        oldContent: selectedRevision.contentBefore,
        newContent: selectedRevision.contentAfter,
        oldRich: selectedRevision.richContentBefore,
        newRich: selectedRevision.richContentAfter,
        sideBySideDiff
      };
    } catch (e) {
      return {
        oldContent: selectedRevision.contentBefore,
        newContent: selectedRevision.contentAfter
      };
    }
  };

  const diffData = getDiffData();

  const renderContentWithFormats = (content, richContent, isOld) => {
    if (!content) return null;

    if (richContent && richContent.content) {
      return (
        <Box sx={{ fontFamily: 'monospace', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {richContent.content.map((block, blockIdx) => (
            <Box key={blockIdx} component="span">
              {block.content.map((textNode, nodeIdx) => {
                const style = {};
                if (textNode.marks) {
                  for (const mark of textNode.marks) {
                    if (mark.type === 'bold') style.fontWeight = 'bold';
                    if (mark.type === 'italic') style.fontStyle = 'italic';
                    if (mark.type === 'underline') style.textDecoration = 'underline';
                    if (mark.type === 'strikethrough') style.textDecoration = 'line-through';
                    if (mark.type === 'color') style.color = mark.color;
                    if (mark.type === 'backgroundColor') style.backgroundColor = mark.color;
                  }
                }
                return (
                  <span key={nodeIdx} style={style}>
                    {textNode.text}
                  </span>
                );
              })}
              {blockIdx < richContent.content.length - 1 && '\n'}
            </Box>
          ))}
        </Box>
      );
    }

    return (
      <Typography 
        sx={{ 
          fontFamily: 'monospace', 
          fontSize: '14px', 
          lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all'
        }}
      >
        {content}
      </Typography>
    );
  };

  const renderInlineDiff = () => {
    if (!selectedRevision) {
      return (
        <Box p={3} textAlign="center">
          <Typography color="text.secondary">请选择一个修订版本查看差异</Typography>
        </Box>
      );
    }

    try {
      const richDiff = JSON.parse(selectedRevision.richDiff);
      
      return (
        <Box sx={{ fontFamily: 'monospace', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {richDiff.map((part, idx) => {
            const style = {};
            
            if (part.added) {
              style.backgroundColor = '#e6ffed';
              style.color = '#22863a';
            } else if (part.removed) {
              style.backgroundColor = '#ffeef0';
              style.color = '#b31d28';
              style.textDecoration = 'line-through';
            }

            if (part.formats) {
              if (part.formats.added.length > 0) {
                for (const f of part.formats.added) {
                  if (f.type === 'bold') style.fontWeight = 'bold';
                  if (f.type === 'italic') style.fontStyle = 'italic';
                  if (f.type === 'underline') style.textDecoration = 'underline';
                  if (f.type === 'color') style.color = f.value;
                  if (f.type === 'backgroundColor') style.backgroundColor = f.value;
                }
              }
              if (part.formats.modified.length > 0) {
                style.borderBottom = '2px dashed #f59e0b';
              }
            }

            return (
              <span key={idx} style={style}>
                {part.value}
              </span>
            );
          })}
        </Box>
      );
    } catch (e) {
      try {
        const diff = JSON.parse(selectedRevision.diff);
        return (
          <Box sx={{ fontFamily: 'monospace', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {diff.map((part, idx) => (
              <span
                key={idx}
                style={{
                  backgroundColor: part.added ? '#e6ffed' : part.removed ? '#ffeef0' : 'transparent',
                  color: part.added ? '#22863a' : part.removed ? '#b31d28' : 'inherit',
                  textDecoration: part.removed ? 'line-through' : 'none'
                }}
              >
                {part.value}
              </span>
            ))}
          </Box>
        );
      } catch (e2) {
        return <Typography color="error">无法加载差异数据</Typography>;
      }
    }
  };

  const renderFormatChanges = () => {
    if (!selectedRevision) return null;

    try {
      const richDiff = JSON.parse(selectedRevision.richDiff);
      const formatChanges = [];

      for (const part of richDiff) {
        if (part.formats && (part.formats.added.length > 0 || part.formats.removed.length > 0 || part.formats.modified.length > 0)) {
          formatChanges.push({
            text: part.value,
            ...part.formats
          });
        }
      }

      if (formatChanges.length === 0) {
        return (
          <Box p={2} bgcolor="grey.50" borderRadius={1}>
            <Typography variant="body2" color="text.secondary">
              此修订不包含格式变更
            </Typography>
          </Box>
        );
      }

      return (
        <Box>
          <Typography variant="subtitle2" gutterBottom>格式变更摘要:</Typography>
          {formatChanges.map((change, idx) => (
            <Box key={idx} mb={2} p={2} bgcolor="grey.50" borderRadius={1}>
              <Typography variant="body2" gutterBottom>
                文本: "{change.text.substring(0, 50)}{change.text.length > 50 ? '...' : ''}"
              </Typography>
              {change.added.length > 0 && (
                <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                  <Typography variant="caption" color="text.secondary">新增格式:</Typography>
                  {change.added.map((f, i) => (
                    <Chip key={i} size="small" color="success" 
                      label={`${f.type}${f.value ? `: ${f.value}` : ''}`} 
                    />
                  ))}
                </Box>
              )}
              {change.removed.length > 0 && (
                <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                  <Typography variant="caption" color="text.secondary">移除格式:</Typography>
                  {change.removed.map((f, i) => (
                    <Chip key={i} size="small" color="error" 
                      label={`${f.type}${f.value ? `: ${f.value}` : ''}`} 
                    />
                  ))}
                </Box>
              )}
              {change.modified.length > 0 && (
                <Box display="flex" gap={1} flexWrap="wrap">
                  <Typography variant="caption" color="text.secondary">修改格式:</Typography>
                  {change.modified.map((f, i) => (
                    <Chip key={i} size="small" color="warning" 
                      label={`${f.type}: ${f.oldValue} → ${f.newValue}`} 
                    />
                  ))}
                </Box>
              )}
            </Box>
          ))}
        </Box>
      );
    } catch (e) {
      return null;
    }
  };

  return (
    <Box>
      <Box mb={3} display="flex" gap={2} alignItems="center">
        <FormControl size="small" sx={{ minWidth: 300 }}>
          <InputLabel>选择修订版本</InputLabel>
          <Select
            value={selectedRevision?._id || ''}
            label="选择修订版本"
            onChange={(e) => {
              const rev = revisions.find(r => r._id === e.target.value);
              setSelectedRevision(rev);
            }}
          >
            {revisions.map((r) => (
              <MenuItem key={r._id} value={r._id}>
                版本 {r.version} - {r.author?.username} - {new Date(r.createdAt).toLocaleString()}
                <Chip 
                  size="small" 
                  color={r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'error' : 'warning'}
                  sx={{ ml: 1 }}
                  label={r.status === 'approved' ? '已通过' : r.status === 'rejected' ? '已拒绝' : '待审核'}
                />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {selectedRevision && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fff5f5' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="subtitle1" color="error">
                    修改前 (版本 {selectedRevision.version - 1})
                  </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                {renderContentWithFormats(
                  selectedRevision.contentBefore, 
                  selectedRevision.richContentBefore,
                  true
                )}
              </Paper>
            </Grid>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f0fdf4' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="subtitle1" color="success">
                    修改后 (版本 {selectedRevision.version})
                  </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                {renderContentWithFormats(
                  selectedRevision.contentAfter, 
                  selectedRevision.richContentAfter,
                  false
                )}
              </Paper>
            </Grid>
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>行内差异对比</Typography>
            <Divider sx={{ mb: 2 }} />
            {renderInlineDiff()}
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            {renderFormatChanges()}
          </Paper>
        </>
      )}
    </Box>
  );
};

export default SideBySideDiff;

import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

const DOC_TYPES = [
  { value: '民事起诉状', label: '民事起诉状' },
  { value: '民事答辩状', label: '民事答辩状' },
  { value: '代理词', label: '代理词' },
];

function DocumentGeneratorPanel({ apiService, description, onGenerate }) {
  const [docType, setDocType] = useState('民事起诉状');
  const [generating, setGenerating] = useState(false);
  const [generatedDoc, setGeneratedDoc] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setGenerating(true);
    setError(null);
    setGeneratedDoc(null);

    try {
      const result = await apiService.generateDocument(description, docType);
      if (result.success && result.document) {
        setGeneratedDoc(result.document);
        if (onGenerate) onGenerate(result.document);
      } else {
        setError('文书生成失败');
      }
    } catch (err) {
      setError('文书生成失败，请稍后重试');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    if (generatedDoc && generatedDoc.content) {
      navigator.clipboard.writeText(generatedDoc.content).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <DescriptionIcon color="primary" />
        文书自动生成
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>文书类型</InputLabel>
          <Select
            value={docType}
            label="文书类型"
            onChange={(e) => setDocType(e.target.value)}
          >
            {DOC_TYPES.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                {type.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          variant="contained"
          onClick={handleGenerate}
          disabled={generating || !description.trim()}
          startIcon={generating ? <CircularProgress size={20} color="inherit" /> : <DescriptionIcon />}
        >
          {generating ? '生成中...' : '生成文书初稿'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {generatedDoc && (
        <>
          <Divider sx={{ my: 2 }} />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" fontWeight="medium">
              {generatedDoc.doc_type}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                字数：{generatedDoc.metadata?.word_count || 0} | 生成时间：{generatedDoc.metadata?.generated_at}
              </Typography>
              <Button
                size="small"
                startIcon={<ContentCopyIcon />}
                onClick={handleCopy}
                color={copied ? 'success' : 'primary'}
              >
                {copied ? '已复制' : '复制'}
              </Button>
            </Box>
          </Box>

          <Paper
            variant="outlined"
            sx={{
              p: 3,
              maxHeight: 500,
              overflow: 'auto',
              bgcolor: '#fafafa',
              fontFamily: '"SimSun", "FangSong", serif',
              fontSize: '14px',
              lineHeight: 2,
              whiteSpace: 'pre-wrap',
            }}
          >
            {generatedDoc.content}
          </Paper>

          {generatedDoc.metadata && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">
                参考案例：{generatedDoc.metadata.reference_cases?.join(', ') || '无'} |
                参考法条：{generatedDoc.metadata.reference_laws?.join(', ') || '无'}
              </Typography>
            </Box>
          )}

          <Alert severity="info" sx={{ mt: 2 }}>
            此文书为系统基于相似案例要素自动生成的初稿，仅供参考。请在律师指导下进行修改和完善。
          </Alert>
        </>
      )}
    </Paper>
  );
}

export default DocumentGeneratorPanel;

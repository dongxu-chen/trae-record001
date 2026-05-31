import React, { useState } from 'react';
import {
  Paper,
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

const caseTypes = [
  { value: '', label: '全部类型' },
  { value: '民间借贷纠纷', label: '民间借贷纠纷' },
  { value: '合同纠纷', label: '合同纠纷' },
  { value: '买卖合同纠纷', label: '买卖合同纠纷' },
  { value: '租赁合同纠纷', label: '租赁合同纠纷' },
  { value: '劳动争议', label: '劳动争议' },
  { value: '交通事故责任纠纷', label: '交通事故责任纠纷' },
];

const sampleCases = [
  '被告向原告借款50万元，约定月利率2%，借款期限6个月，到期后被告未还款',
  '原被告签订货物买卖合同，原告供货后被告拖欠货款35万元',
  '被告承租原告房屋，拖欠租金8个月共计48000元',
];

function SearchForm({ onSearch, loading }) {
  const [description, setDescription] = useState('');
  const [caseType, setCaseType] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (description.trim()) {
      onSearch(description, caseType);
    }
  };

  const handleSampleClick = (sample) => {
    setDescription(sample);
  };

  return (
    <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom sx={{ mb: 3 }}>
        案例检索
      </Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          multiline
          rows={6}
          label="请输入案情描述"
          placeholder="请详细描述您的案件情况，包括：当事人、案件事实、争议焦点等信息..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          sx={{ mb: 2 }}
          variant="outlined"
        />
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          示例案情：
        </Typography>
        <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {sampleCases.map((sample, index) => (
            <Button
              key={index}
              size="small"
              variant="outlined"
              onClick={() => handleSampleClick(sample)}
              sx={{ textTransform: 'none' }}
            >
              示例 {index + 1}
            </Button>
          ))}
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>案件类型</InputLabel>
            <Select
              value={caseType}
              label="案件类型"
              onChange={(e) => setCaseType(e.target.value)}
            >
              {caseTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            type="submit"
            variant="contained"
            size="large"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
            disabled={loading || !description.trim()}
            sx={{ height: 56 }}
          >
            {loading ? '检索中...' : '检索相似案例'}
          </Button>
        </Box>
      </form>
    </Paper>
  );
}

export default SearchForm;

import React, { useState } from 'react';
import { 
  Box, IconButton, Divider, Tooltip, Menu, MenuItem, 
  ListItemIcon, ListItemText
} from '@mui/material';
import FormatBoldIcon from '@mui/icons-material/FormatBold';
import FormatItalicIcon from '@mui/icons-material/FormatItalic';
import FormatUnderlinedIcon from '@mui/icons-material/FormatUnderlined';
import FormatStrikethroughIcon from '@mui/icons-material/FormatStrikethrough';
import FormatColorTextIcon from '@mui/icons-material/FormatColorText';
import FormatColorFillIcon from '@mui/icons-material/FormatColorFill';
import TableChartIcon from '@mui/icons-material/TableChart';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';

const FormatToolbar = ({ onFormat, onTableOperation, disabled }) => {
  const [colorAnchor, setColorAnchor] = useState(null);
  const [bgColorAnchor, setBgColorAnchor] = useState(null);
  const [tableAnchor, setTableAnchor] = useState(null);

  const colors = [
    { name: '黑色', value: '#000000' },
    { name: '红色', value: '#dc2626' },
    { name: '蓝色', value: '#2563eb' },
    { name: '绿色', value: '#16a34a' },
    { name: '黄色', value: '#ca8a04' },
    { name: '紫色', value: '#9333ea' },
    { name: '橙色', value: '#ea580c' },
  ];

  const bgColors = [
    { name: '无背景', value: 'transparent' },
    { name: '黄色高亮', value: '#fef08a' },
    { name: '绿色高亮', value: '#bbf7d0' },
    { name: '蓝色高亮', value: '#bfdbfe' },
    { name: '红色高亮', value: '#fecaca' },
    { name: '紫色高亮', value: '#e9d5ff' },
    { name: '灰色高亮', value: '#e5e7eb' },
  ];

  const handleBold = () => onFormat('bold');
  const handleItalic = () => onFormat('italic');
  const handleUnderline = () => onFormat('underline');
  const handleStrikethrough = () => onFormat('strikethrough');

  const handleColorSelect = (color) => {
    onFormat('color', color);
    setColorAnchor(null);
  };

  const handleBgColorSelect = (color) => {
    onFormat('backgroundColor', color);
    setBgColorAnchor(null);
  };

  const handleTableOperation = (action) => {
    onTableOperation(action);
    setTableAnchor(null);
  };

  return (
    <Box 
      sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 0.5, 
        p: 1, 
        borderBottom: 1, 
        borderColor: 'divider',
        bgcolor: 'grey.50'
      }}
    >
      <Tooltip title="加粗">
        <span>
          <IconButton 
            size="small" 
            onClick={handleBold}
            disabled={disabled}
          >
            <FormatBoldIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      
      <Tooltip title="斜体">
        <span>
          <IconButton 
            size="small" 
            onClick={handleItalic}
            disabled={disabled}
          >
            <FormatItalicIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      
      <Tooltip title="下划线">
        <span>
          <IconButton 
            size="small" 
            onClick={handleUnderline}
            disabled={disabled}
          >
            <FormatUnderlinedIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      
      <Tooltip title="删除线">
        <span>
          <IconButton 
            size="small" 
            onClick={handleStrikethrough}
            disabled={disabled}
          >
            <FormatStrikethroughIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>

      <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />

      <Tooltip title="文字颜色">
        <span>
          <IconButton 
            size="small"
            onClick={(e) => setColorAnchor(e.currentTarget)}
            disabled={disabled}
          >
            <FormatColorTextIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Menu
        anchorEl={colorAnchor}
        open={Boolean(colorAnchor)}
        onClose={() => setColorAnchor(null)}
      >
        {colors.map((color) => (
          <MenuItem key={color.value} onClick={() => handleColorSelect(color.value)}>
            <ListItemIcon>
              <Box 
                sx={{ 
                  width: 20, 
                  height: 20, 
                  bgcolor: color.value,
                  border: 1,
                  borderColor: 'divider'
                }} 
              />
            </ListItemIcon>
            <ListItemText>{color.name}</ListItemText>
          </MenuItem>
        ))}
      </Menu>

      <Tooltip title="背景颜色">
        <span>
          <IconButton 
            size="small"
            onClick={(e) => setBgColorAnchor(e.currentTarget)}
            disabled={disabled}
          >
            <FormatColorFillIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Menu
        anchorEl={bgColorAnchor}
        open={Boolean(bgColorAnchor)}
        onClose={() => setBgColorAnchor(null)}
      >
        {bgColors.map((color) => (
          <MenuItem key={color.value} onClick={() => handleBgColorSelect(color.value)}>
            <ListItemIcon>
              <Box 
                sx={{ 
                  width: 20, 
                  height: 20, 
                  bgcolor: color.value,
                  border: 1,
                  borderColor: 'divider'
                }} 
              />
            </ListItemIcon>
            <ListItemText>{color.name}</ListItemText>
          </MenuItem>
        ))}
      </Menu>

      <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />

      <Tooltip title="表格操作">
        <span>
          <IconButton 
            size="small"
            onClick={(e) => setTableAnchor(e.currentTarget)}
            disabled={disabled}
          >
            <TableChartIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Menu
        anchorEl={tableAnchor}
        open={Boolean(tableAnchor)}
        onClose={() => setTableAnchor(null)}
      >
        <MenuItem onClick={() => handleTableOperation('insert-row-above')}>
          <ListItemIcon><AddIcon fontSize="small" /></ListItemIcon>
          <ListItemText>在上方插入行</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleTableOperation('insert-row-below')}>
          <ListItemIcon><AddIcon fontSize="small" /></ListItemIcon>
          <ListItemText>在下方插入行</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleTableOperation('delete-row')}>
          <ListItemIcon><DeleteIcon fontSize="small" /></ListItemIcon>
          <ListItemText>删除当前行</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => handleTableOperation('insert-column-left')}>
          <ListItemIcon><AddIcon fontSize="small" /></ListItemIcon>
          <ListItemText>在左侧插入列</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleTableOperation('insert-column-right')}>
          <ListItemIcon><AddIcon fontSize="small" /></ListItemIcon>
          <ListItemText>在右侧插入列</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleTableOperation('delete-column')}>
          <ListItemIcon><DeleteIcon fontSize="small" /></ListItemIcon>
          <ListItemText>删除当前列</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default FormatToolbar;

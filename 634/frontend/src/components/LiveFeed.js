import React from 'react';
import { 
  Paper, List, ListItem, ListItemText, Typography, 
  Box, Chip, Divider
} from '@mui/material';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

function LiveFeed({ articles }) {
  const formatTime = (timeStr) => {
    try {
      return format(new Date(timeStr), 'HH:mm:ss', { locale: zhCN });
    } catch {
      return timeStr;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">实时新闻流</Typography>
        <Chip label={`已接收: ${articles.length}`} size="small" color="primary" />
      </Box>

      <Paper sx={{ maxHeight: '70vh', overflow: 'auto' }}>
        <List>
          {articles.map((article, index) => (
            <React.Fragment key={article.id || index}>
              <ListItem alignItems="flex-start">
                <Box mr={2}>
                  <Typography 
                    variant="caption" 
                    color="textSecondary"
                    sx={{ whiteSpace: 'nowrap' }}
                  >
                    {formatTime(article.publish_time)}
                  </Typography>
                </Box>
                <ListItemText
                  primary={
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {article.title}
                    </Typography>
                  }
                  secondary={
                    <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                      <Chip 
                        label={article.source} 
                        size="small" 
                        variant="outlined"
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                      {article.topic_id && (
                        <Chip 
                          label={`话题: ${article.topic_id.slice(0, 8)}`}
                          size="small"
                          color="primary"
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      )}
                    </Box>
                  }
                />
              </ListItem>
              {index < articles.length - 1 && <Divider variant="inset" component="li" />}
            </React.Fragment>
          ))}
          {articles.length === 0 && (
            <ListItem>
              <ListItemText 
                primary={
                  <Typography color="textSecondary" align="center">
                    等待新闻数据...
                    <br />
                    <Typography variant="caption">
                      点击顶部"生成模拟数据"按钮开始测试
                    </Typography>
                  </Typography>
                }
              />
            </ListItem>
          )}
        </List>
      </Paper>
    </Box>
  );
}

export default LiveFeed;

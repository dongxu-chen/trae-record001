import React, { useState, useEffect } from 'react';
import { Box, AppBar, Toolbar, Typography, Button, Container, Tabs, Tab, Snackbar, Alert, Badge } from '@mui/material';
import { Warning as WarningIcon } from '@mui/icons-material';
import { wsService } from './services/websocketService';
import { newsApi } from './services/api';
import TopicList from './components/TopicList';
import EvolutionGraph from './components/EvolutionGraph';
import TopicDetail from './components/TopicDetail';
import LiveFeed from './components/LiveFeed';
import BurstingTopics from './components/BurstingTopics';
import TopicWarnings from './components/TopicWarnings';
import PropagationTracker from './components/PropagationTracker';
import TopicComparison from './components/TopicComparison';

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [notification, setNotification] = useState(null);
  const [liveArticles, setLiveArticles] = useState([]);
  const [warningCount, setWarningCount] = useState(0);

  useEffect(() => {
    wsService.connect();

    wsService.addListener('open', () => setIsConnected(true));
    wsService.addListener('close', () => setIsConnected(false));
    
    wsService.addListener('topic_update', (data) => {
      showNotification(`话题更新: ${data.name}`, 'info');
    });

    wsService.addListener('evolution', (data) => {
      showNotification(`话题演化: ${data.type}`, 'success');
    });

    wsService.addListener('new_article', (data) => {
      setLiveArticles(prev => [data, ...prev].slice(0, 50));
    });

    wsService.addListener('topic_warning', (data) => {
      showNotification(`⚠️ 话题预警: ${data.topic_name}`, 'warning');
      setWarningCount(prev => prev + 1);
    });

    return () => {
      wsService.disconnect();
    };
  }, []);

  const showNotification = (message, severity = 'info') => {
    setNotification({ message, severity });
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleTopicSelect = (topic) => {
    setSelectedTopic(topic);
    setTabValue(2);
  };

  const generateMockData = async () => {
    try {
      await newsApi.generateMock(10);
      showNotification('已生成10条模拟新闻', 'success');
    } catch (error) {
      showNotification('生成模拟数据失败', 'error');
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            新闻话题演化追踪系统
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              {isConnected ? '🟢 实时连接' : '🔴 连接断开'}
            </Typography>
            <Button color="inherit" onClick={generateMockData}>
              生成模拟数据
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }} variant="scrollable" scrollButtons="auto">
          <Tab label="话题列表" />
          <Tab label="演化图谱" />
          <Tab label="话题详情" />
          <Tab label="实时动态" />
          <Tab label="爆发话题" />
          <Tab 
            label={
              <Badge badgeContent={warningCount} color="error" max={99}>
                话题预警
              </Badge>
            } 
          />
          <Tab label="传播溯源" />
          <Tab label="话题对比" />
        </Tabs>

        {tabValue === 0 && (
          <TopicList onTopicSelect={handleTopicSelect} />
        )}
        
        {tabValue === 1 && (
          <EvolutionGraph onTopicSelect={handleTopicSelect} />
        )}
        
        {tabValue === 2 && (
          <TopicDetail topicId={selectedTopic?.topic_id} />
        )}
        
        {tabValue === 3 && (
          <LiveFeed articles={liveArticles} />
        )}
        
        {tabValue === 4 && (
          <BurstingTopics onTopicSelect={handleTopicSelect} />
        )}

        {tabValue === 5 && (
          <TopicWarnings onTopicSelect={(topicId) => { setSelectedTopic({ topic_id: topicId }); setTabValue(2); }} />
        )}

        {tabValue === 6 && (
          <PropagationTracker 
            topicId={selectedTopic?.topic_id} 
            topicName={selectedTopic?.name} 
          />
        )}

        {tabValue === 7 && (
          <TopicComparison />
        )}
      </Container>

      <Snackbar 
        open={!!notification} 
        autoHideDuration={3000} 
        onClose={() => setNotification(null)}
      >
        <Alert 
          severity={notification?.severity} 
          onClose={() => setNotification(null)}
        >
          {notification?.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default App;

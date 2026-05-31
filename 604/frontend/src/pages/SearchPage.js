import React, { useState } from 'react';
import {
  Typography, Box, Alert, CircularProgress, Divider, Tabs, Tab } from '@mui/material';
import SearchForm from '../components/SearchForm';
import QueryAnalysis from '../components/QueryAnalysis';
import CaseCard from '../components/CaseCard';
import LawRecommendation from '../components/LawRecommendation';
import JudgmentPrediction from '../components/JudgmentPrediction';
import DisputeFocusAnalysis from '../components/DisputeFocusAnalysis';
import DocumentGeneratorPanel from '../components/DocumentGeneratorPanel';

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 3 }}>{children}</Box> : null;
}

function SearchPage({ apiService }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [searchDescription, setSearchDescription] = useState('');

  const handleSearch = async (description, caseType) => {
    setLoading(true);
    setError(null);
    setTabValue(0);

    try {
      const result = await apiService.searchCases(description, 10, caseType || null);
      setSearchResult(result);
      setSearchDescription(description);
    } catch (err) {
      setError('检索失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <SearchForm onSearch={handleSearch} loading={loading} />

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {searchResult && !loading && (
        <>
          <QueryAnalysis analysis={searchResult.query_analysis} />

          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 1 }}>
            <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} variant="scrollable" scrollButtons="auto">
              <Tab label={`相似案例 (${searchResult.similar_cases.length})`} />
              <Tab label="判决预测" />
              <Tab label="争议焦点分析" />
              <Tab label="文书生成" />
              <Tab label="法条推荐" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            {searchResult.similar_cases.length > 0 ? (
              searchResult.similar_cases.map((caseItem, index) => (
                <CaseCard key={caseItem.case_id} caseData={caseItem} index={index} />
              ))
            ) : (
              <Alert severity="info">未找到相似案例</Alert>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <JudgmentPrediction prediction={searchResult.judgment_prediction} />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <DisputeFocusAnalysis analysis={searchResult.dispute_analysis} />
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <DocumentGeneratorPanel
              apiService={apiService}
              description={searchDescription}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <LawRecommendation laws={searchResult.recommended_law_articles} />
          </TabPanel>
        </>
      )}
    </Box>
  );
}

export default SearchPage;

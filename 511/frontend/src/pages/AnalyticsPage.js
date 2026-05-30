import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Tab,
  Tabs,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Alert,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DownloadIcon from '@mui/icons-material/Download';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import InfoIcon from '@mui/icons-material/Info';
import {
  getAllTables,
  analyzeImpact,
  getDataDictionary,
  getLineageDocument,
  getMarkdownDocument,
  detectAnomalies,
} from '../services/api';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

function AnalyticsPage() {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [impactData, setImpactData] = useState(null);
  const [dataDictionary, setDataDictionary] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [showMarkdown, setShowMarkdown] = useState(false);

  useEffect(() => {
    loadTables();
  }, []);

  const loadTables = async () => {
    try {
      const response = await getAllTables();
      setTables(response.data.tables);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleAnalyzeImpact = async () => {
    if (!selectedTable) return;
    setLoading(true);
    setError('');
    try {
      const response = await analyzeImpact(selectedTable);
      setImpactData(response.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDataDictionary = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getDataDictionary();
      setDataDictionary(response.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDetectAnomalies = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await detectAnomalies();
      setAnomalies(response.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportMarkdown = async () => {
    try {
      const response = await getMarkdownDocument();
      setMarkdown(response.data);
      setShowMarkdown(true);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data_lineage_document.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <ErrorIcon color="error" />;
      case 'medium':
        return <WarningIcon color="warning" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">数据分析</Typography>
        <Button variant="outlined" onClick={() => navigate('/')}>
          返回解析
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab label="影响分析" />
          <Tab label="数据字典" />
          <Tab label="文档生成" />
          <Tab label="异常检测" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              源表影响下游分析
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <FormControl sx={{ minWidth: 300 }}>
                <InputLabel>选择源表</InputLabel>
                <Select
                  value={selectedTable}
                  label="选择源表"
                  onChange={(e) => setSelectedTable(e.target.value)}
                >
                  {tables.map((table) => (
                    <MenuItem key={table.full_name} value={table.full_name}>
                      {table.full_name} ({table.node_type})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="contained"
                onClick={handleAnalyzeImpact}
                disabled={!selectedTable || loading}
              >
                分析影响
              </Button>
            </Box>
          </CardContent>
        </Card>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {impactData && (
          <>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  影响分析结果
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3 }}>
                  <Chip label={`影响表数: ${impactData.total_tables_impacted}`} color="primary" />
                  <Chip label={`影响字段数: ${impactData.total_columns_impacted}`} color="success" />
                  <Chip label={`最大影响深度: ${impactData.max_impact_depth}`} color="warning" />
                </Box>

                <Typography variant="subtitle1" sx={{ mb: 2 }}>
                  下游受影响的表:
                </Typography>
                <TableContainer component={Paper}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>表名</TableCell>
                        <TableCell>影响层级</TableCell>
                        <TableCell>直接影响数</TableCell>
                        <TableCell>总影响数</TableCell>
                        <TableCell>影响路径</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {impactData.downstream_tables?.map((table, idx) => (
                        <TableRow key={idx}>
                          <TableCell sx={{ fontFamily: 'monospace' }}>
                            {table.name}
                          </TableCell>
                          <TableCell>
                            <Chip label={`第 ${table.level} 层`} size="small" />
                          </TableCell>
                          <TableCell>{table.direct_impacts}</TableCell>
                          <TableCell>{table.total_impacts}</TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '12px' }}>
                            {table.impact_path?.join(' → ')}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                {impactData.downstream_columns?.length > 0 && (
                  <>
                    <Typography variant="subtitle1" sx={{ mt: 3, mb: 2 }}>
                      下游受影响的字段 (前20条):
                    </Typography>
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>字段名</TableCell>
                            <TableCell>影响层级</TableCell>
                            <TableCell>直接影响数</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {impactData.downstream_columns?.slice(0, 20).map((col, idx) => (
                            <TableRow key={idx}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>
                                {col.name}
                              </TableCell>
                              <TableCell>
                                <Chip label={`第 ${col.level} 层`} size="small" />
                              </TableCell>
                              <TableCell>{col.direct_impacts}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mb: 3 }}>
          <Button
            variant="contained"
            onClick={handleLoadDataDictionary}
            disabled={loading}
          >
            生成数据字典
          </Button>
        </Box>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {dataDictionary && (
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  数据字典
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip label={`总表数: ${dataDictionary.total_tables}`} color="primary" />
                  <Chip label={`总字段数: ${dataDictionary.total_columns}`} color="success" />
                  <Chip label={`生成时间: ${dataDictionary.generated_at?.slice(0, 19)}`} />
                </Box>
              </Box>

              {dataDictionary.tables?.map((table, idx) => (
                <Accordion key={idx} sx={{ mb: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                      <Typography sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}>
                        {table.database && `${table.database}.`}
                        {table.table_schema && `${table.table_schema}.`}
                        {table.name}
                      </Typography>
                      <Chip label={table.node_type} size="small"
                        color={
                          table.node_type === 'source' ? 'success' :
                          table.node_type === 'target' ? 'error' :
                          table.node_type === 'cte' ? 'warning' : 'default'
                        }
                      />
                      <Chip label={`${table.columns?.length} 字段`} size="small" />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ mb: 2 }}>
                      {table.source_tables?.length > 0 && (
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>源表:</strong> {table.source_tables.join(', ')}
                        </Typography>
                      )}
                      {table.target_tables?.length > 0 && (
                        <Typography variant="body2">
                          <strong>下游表:</strong> {table.target_tables.join(', ')}
                        </Typography>
                      )}
                    </Box>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>字段名</TableCell>
                            <TableCell>源字段</TableCell>
                            <TableCell>转换逻辑/映射链</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {table.columns?.map((col, colIdx) => (
                            <TableRow key={colIdx}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>
                                {col.name}
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '12px' }}>
                                {col.source_columns?.join(', ') || '-'}
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '12px', maxWidth: 400 }}>
                                {col.transformation || col.mapping_chain || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              数据血缘文档生成
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              <Button
                variant="contained"
                onClick={handleLoadDataDictionary}
                disabled={loading}
              >
                生成JSON文档
              </Button>
              <Button
                variant="outlined"
                onClick={handleExportMarkdown}
                startIcon={<DownloadIcon />}
                disabled={loading}
              >
                导出Markdown文档
              </Button>
            </Box>

            {loading && <LinearProgress sx={{ mb: 2 }} />}

            {dataDictionary && !showMarkdown && (
              <Box>
                <Typography variant="subtitle1" sx={{ mb: 2 }}>
                  文档概览
                </Typography>
                <TableContainer component={Paper}>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>总表数</TableCell>
                        <TableCell>{dataDictionary.total_tables}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>总字段数</TableCell>
                        <TableCell>{dataDictionary.total_columns}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>生成时间</TableCell>
                        <TableCell>{dataDictionary.generated_at}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {showMarkdown && (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="subtitle1">Markdown 文档</Typography>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={handleDownloadMarkdown}
                    startIcon={<DownloadIcon />}
                  >
                    下载文档
                  </Button>
                </Box>
                <Paper sx={{ p: 2, maxHeight: 500, overflow: 'auto' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>
                    {markdown}
                  </pre>
                </Paper>
              </Box>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Box sx={{ mb: 3 }}>
          <Button
            variant="contained"
            onClick={handleDetectAnomalies}
            disabled={loading}
          >
            检测异常
          </Button>
        </Box>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {anomalies && (
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">
                  异常检测结果
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip label={`总异常数: ${anomalies.total_anomalies}`} color={anomalies.total_anomalies > 0 ? 'warning' : 'success'} />
                  {anomalies.by_severity?.critical > 0 && (
                    <Chip label={`严重: ${anomalies.by_severity.critical}`} color="error" />
                  )}
                  {anomalies.by_severity?.high > 0 && (
                    <Chip label={`高危: ${anomalies.by_severity.high}`} color="error" />
                  )}
                  {anomalies.by_severity?.medium > 0 && (
                    <Chip label={`中危: ${anomalies.by_severity.medium}`} color="warning" />
                  )}
                  {anomalies.by_severity?.low > 0 && (
                    <Chip label={`低危: ${anomalies.by_severity.low}`} color="info" />
                  )}
                </Box>
              </Box>

              {anomalies.summary && (
                <Alert severity={anomalies.total_anomalies > 0 ? 'warning' : 'success'} sx={{ mb: 3 }}>
                  {anomalies.summary}
                </Alert>
              )}

              {anomalies.anomalies?.length === 0 ? (
                <Alert severity="success">
                  未检测到异常，所有血缘关系正常！
                </Alert>
              ) : (
                <List>
                  {anomalies.anomalies?.map((anomaly, idx) => (
                    <React.Fragment key={idx}>
                      <ListItem alignItems="flex-start">
                        <Box sx={{ display: 'flex', width: '100%', gap: 2 }}>
                          {getSeverityIcon(anomaly.severity)}
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <Chip
                                label={anomaly.anomaly_type?.replace(/_/g, ' ')}
                                size="small"
                                color={getSeverityColor(anomaly.severity)}
                              />
                              <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                {anomaly.description}
                              </Typography>
                            </Box>
                            
                            {anomaly.affected_objects?.length > 0 && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                  影响对象 ({anomaly.affected_objects.length}个):
                                </Typography>
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                  {anomaly.affected_objects.slice(0, 10).map((obj, i) => (
                                    <Chip
                                      key={i}
                                      label={obj}
                                      size="small"
                                      variant="outlined"
                                      sx={{ fontFamily: 'monospace', fontSize: '10px' }}
                                    />
                                  ))}
                                  {anomaly.affected_objects.length > 10 && (
                                    <Chip
                                      label={`+${anomaly.affected_objects.length - 10} 更多`}
                                      size="small"
                                      variant="outlined"
                                    />
                                  )}
                                </Box>
                              </Box>
                            )}

                            {anomaly.recommendation && (
                              <Typography variant="body2" color="text.secondary">
                                <strong>建议:</strong> {anomaly.recommendation}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </ListItem>
                      {idx < anomalies.anomalies.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        )}
      </TabPanel>
    </Box>
  );
}

export default AnalyticsPage;

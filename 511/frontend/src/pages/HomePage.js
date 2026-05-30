import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import { parseSQL, saveLineage } from '../services/api';

const sampleSQLs = [
  {
    name: 'CREATE TABLE AS SELECT (基础)',
    sql: `CREATE TABLE analytics.user_summary
AS
SELECT 
    u.user_id,
    u.user_name,
    COUNT(o.order_id) as order_count,
    SUM(o.amount) as total_amount
FROM raw.users u
JOIN raw.orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.user_name`,
  },
  {
    name: 'INSERT WITH CTE (复杂)',
    sql: `INSERT INTO analytics.monthly_report (user_id, month, revenue)
WITH user_orders AS (
    SELECT 
        user_id,
        order_id,
        amount,
        DATE_TRUNC('month', order_date) as order_month
    FROM raw.orders
    WHERE status = 'completed'
),
user_payments AS (
    SELECT 
        uo.user_id,
        uo.order_month,
        SUM(uo.amount) as monthly_revenue
    FROM user_orders uo
    GROUP BY uo.user_id, uo.order_month
)
SELECT 
    up.user_id,
    up.order_month as month,
    up.monthly_revenue as revenue
FROM user_payments up
JOIN raw.users u ON up.user_id = u.user_id
WHERE u.country = 'CN'`,
  },
  {
    name: 'UNION 多表合并',
    sql: `CREATE TABLE unified.transactions
AS
SELECT 
    t1.transaction_id,
    t1.user_id,
    t1.amount,
    t1.created_at,
    'source_a' as source
FROM source_a.transactions t1
WHERE t1.status = 'success'

UNION ALL

SELECT 
    t2.txn_id as transaction_id,
    t2.customer_id as user_id,
    t2.value as amount,
    t2.timestamp as created_at,
    'source_b' as source
FROM source_b.txns t2
WHERE t2.is_valid = 1`,
  },
  {
    name: '子查询嵌套',
    sql: `CREATE TABLE analytics.top_customers
AS
SELECT
    user_id,
    user_name,
    total_orders,
    total_spent
FROM (
    SELECT
        u.user_id,
        u.user_name,
        (SELECT COUNT(*) FROM raw.orders o WHERE o.user_id = u.user_id) as total_orders,
        (SELECT SUM(amount) FROM raw.orders o WHERE o.user_id = u.user_id) as total_spent
    FROM raw.users u
) sub
WHERE total_orders > 10
ORDER BY total_spent DESC
LIMIT 100`,
  },
];

function HomePage() {
  const navigate = useNavigate();
  const [sql, setSql] = useState(sampleSQLs[0].sql);
  const [database, setDatabase] = useState('');
  const [schema, setSchema] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [tabValue, setTabValue] = useState(0);

  const handleParse = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await parseSQL(sql, database || null, schema || null);
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await saveLineage(sql, database || null, schema || null);
      setResult(response.data);
      navigate('/graph');
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSampleSelect = (index) => {
    setSql(sampleSQLs[index].sql);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        SQL 血缘解析
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Tabs
                value={tabValue}
                onChange={(e, v) => setTabValue(v)}
                variant="scrollable"
                sx={{ mb: 2 }}
              >
                <Tab label="编辑器" />
                {sampleSQLs.map((sample, idx) => (
                  <Tab
                    key={idx}
                    label={sample.name}
                    onClick={() => handleSampleSelect(idx)}
                  />
                ))}
              </Tabs>

              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <TextField
                    label="数据库 (可选)"
                    value={database}
                    onChange={(e) => setDatabase(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    label="Schema (可选)"
                    value={schema}
                    onChange={(e) => setSchema(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
              </Grid>

              <TextField
                label="SQL 语句"
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                multiline
                rows={15}
                fullWidth
                variant="outlined"
                sx={{ mb: 2, fontFamily: 'monospace' }}
              />

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<PlayArrowIcon />}
                  onClick={handleParse}
                  disabled={loading}
                >
                  解析
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<SaveIcon />}
                  onClick={handleSave}
                  disabled={loading}
                >
                  解析并保存
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/graph')}
                >
                  查看图谱
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {result && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  解析结果
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="primary">
                    涉及的表 ({result.tables.length})
                  </Typography>
                  {result.tables.map((table, idx) => (
                    <Typography key={idx} variant="body2">
                      - {table.full_name}
                    </Typography>
                  ))}
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="primary">
                    字段血缘关系 ({result.column_lineage.length})
                  </Typography>
                  {result.column_lineage.slice(0, 10).map((lineage, idx) => (
                    <Typography key={idx} variant="body2">
                      {lineage.source.full_name} → {lineage.target.full_name}
                    </Typography>
                  ))}
                  {result.column_lineage.length > 10 && (
                    <Typography variant="body2" color="text.secondary">
                      ... 还有 {result.column_lineage.length - 10} 条
                    </Typography>
                  )}
                </Box>

                {result.cte_tables.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" color="primary">
                      CTE 临时表
                    </Typography>
                    {result.cte_tables.map((cte, idx) => (
                      <Typography key={idx} variant="body2">
                        - {cte}
                      </Typography>
                    ))}
                  </Box>
                )}

                <Paper sx={{ p: 2, maxHeight: 200, overflow: 'auto' }}>
                  <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(result, null, 2)}
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}

export default HomePage;

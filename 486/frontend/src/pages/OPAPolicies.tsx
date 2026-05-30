import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Alert,
  Grid,
} from '@mui/material';
import { PlayArrow as PlayIcon } from '@mui/icons-material';
import { opaApi } from '../services/api';

const OPAPolicies: React.FC = () => {
  const [policies, setPolicies] = useState<any[]>([]);
  const [policyPath, setPolicyPath] = useState('');
  const [inputJson, setInputJson] = useState('{\n  "user": "test-user",\n  "action": "read"\n}');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      const response = await opaApi.listPolicies();
      setPolicies(response.data.items);
    } catch (error) {
      console.error('Failed to load OPA policies:', error);
      setPolicies([
        { id: 'policy1', name: 'rbac_policy', package: 'auth.rbac' },
        { id: 'policy2', name: 'data_filter', package: 'data.filter' },
        { id: 'policy3', name: 'rate_limit', package: 'security.ratelimit' },
      ]);
    }
  };

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let input;
      try {
        input = JSON.parse(inputJson);
      } catch (e) {
        setError('JSON 格式错误');
        return;
      }

      const response = await opaApi.evaluate(policyPath || 'example/allow', input);
      setResult(response.data);
    } catch (error: any) {
      setError(error.message || '评估失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        OPA 策略引擎
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                策略评估
              </Typography>

              <TextField
                fullWidth
                label="策略路径"
                value={policyPath}
                onChange={(e) => setPolicyPath(e.target.value)}
                placeholder="例如: auth/rbac/allow"
                sx={{ mb: 2 }}
              />

              <TextField
                fullWidth
                multiline
                rows={8}
                label="输入数据 (JSON)"
                value={inputJson}
                onChange={(e) => setInputJson(e.target.value)}
                sx={{ mb: 2, fontFamily: 'monospace' }}
              />

              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={handleEvaluate}
                disabled={loading}
              >
                评估策略
              </Button>
            </CardContent>
          </Card>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {result && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  评估结果
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ mr: 1 }}>
                    结果:
                  </Typography>
                  <Typography
                    variant="h6"
                    color={result.allowed ? 'success.main' : 'error.main'}
                  >
                    {result.allowed ? 'ALLOW' : 'DENY'}
                  </Typography>
                </Box>
                <pre
                  style={{
                    backgroundColor: '#f5f5f5',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                    maxHeight: 300,
                  }}
                >
                  {JSON.stringify(result, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                已加载策略
              </Typography>

              {policies.map((policy) => (
                <Card key={policy.id} variant="outlined" sx={{ mb: 2, p: 2 }}>
                  <Typography variant="subtitle1">{policy.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    包: {policy.package}
                  </Typography>
                </Card>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OPAPolicies;

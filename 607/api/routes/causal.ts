import express, { type Request, type Response } from 'express';
import axios from 'axios';

const router = express.Router();

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:5001';

router.post('/preview', async (req: Request, res: Response) => {
  try {
    const { data } = req.body;
    const response = await axios.post(`${PYTHON_API_URL}/api/preview`, { data }, {
      timeout: 30000,
    });
    res.json(response.data);
  } catch (error) {
    console.error('Preview error:', error);
    if (axios.isAxiosError(error)) {
      res.status(error.response?.status || 500).json({
        error: error.response?.data?.error || 'Failed to preview data',
      });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.post('/lasso-select', async (req: Request, res: Response) => {
  try {
    const { data, treatment, outcome, candidate_covariates, method, max_features } = req.body;
    const response = await axios.post(`${PYTHON_API_URL}/api/lasso-select`, {
      data,
      treatment,
      outcome,
      candidate_covariates,
      method,
      max_features,
    }, {
      timeout: 60000,
    });
    res.json(response.data);
  } catch (error) {
    console.error('LASSO selection error:', error);
    if (axios.isAxiosError(error)) {
      res.status(error.response?.status || 500).json({
        error: error.response?.data?.error || 'Failed to perform LASSO selection',
      });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.post('/analyze/psm', async (req: Request, res: Response) => {
  try {
    const { data, treatment, outcome, covariates, useAutoSelection, autoSelectionMethod } = req.body;
    const response = await axios.post(`${PYTHON_API_URL}/api/analyze/psm`, {
      data,
      treatment,
      outcome,
      covariates,
      useAutoSelection,
      autoSelectionMethod,
    }, {
      timeout: 120000,
    });
    res.json(response.data);
  } catch (error) {
    console.error('PSM analysis error:', error);
    if (axios.isAxiosError(error)) {
      res.status(error.response?.status || 500).json({
        error: error.response?.data?.error || 'Failed to perform PSM analysis',
      });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.post('/analyze/did', async (req: Request, res: Response) => {
  try {
    const { data, treatment, outcome, covariates, timeVariable, postTreatmentIndicator, useAutoSelection, autoSelectionMethod } = req.body;
    const response = await axios.post(`${PYTHON_API_URL}/api/analyze/did`, {
      data,
      treatment,
      outcome,
      covariates,
      timeVariable,
      postTreatmentIndicator,
      useAutoSelection,
      autoSelectionMethod,
    }, {
      timeout: 120000,
    });
    res.json(response.data);
  } catch (error) {
    console.error('DID analysis error:', error);
    if (axios.isAxiosError(error)) {
      res.status(error.response?.status || 500).json({
        error: error.response?.data?.error || 'Failed to perform DID analysis',
      });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.post('/generate-report', async (req: Request, res: Response) => {
  try {
    const { result, method, treatment, outcome, covariates, sampleSize, format } = req.body;
    const response = await axios.post(`${PYTHON_API_URL}/api/generate-report`, {
      result,
      method,
      treatment,
      outcome,
      covariates,
      sampleSize,
      format,
    }, {
      timeout: 60000,
    });
    res.json(response.data);
  } catch (error) {
    console.error('Report generation error:', error);
    if (axios.isAxiosError(error)) {
      res.status(error.response?.status || 500).json({
        error: error.response?.data?.error || 'Failed to generate report',
      });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.get('/python-health', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/api/health`, {
      timeout: 5000,
    });
    res.json(response.data);
  } catch (error) {
    res.status(503).json({
      status: 'unavailable',
      message: 'Python API server is not available',
    });
  }
});

export default router;

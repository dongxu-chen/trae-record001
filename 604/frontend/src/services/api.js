import axios from 'axios';

class ApiService {
  constructor(baseURL = '') {
    this.client = axios.create({
      baseURL,
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async searchCases(description, topK = 10, caseType = null) {
    try {
      const response = await this.client.post('/api/search', {
        description,
        top_k: topK,
        case_type: caseType,
      });
      return response.data;
    } catch (error) {
      console.error('搜索失败:', error);
      throw error;
    }
  }

  async analyzeCase(description) {
    try {
      const response = await this.client.post('/api/analyze', null, {
        params: { description },
      });
      return response.data;
    } catch (error) {
      console.error('分析失败:', error);
      throw error;
    }
  }

  async getCaseDetail(caseId) {
    try {
      const response = await this.client.get(`/api/cases/${caseId}`);
      return response.data;
    } catch (error) {
      console.error('获取案例详情失败:', error);
      throw error;
    }
  }

  async predictJudgment(description, topK = 10, caseType = null) {
    try {
      const response = await this.client.post('/api/predict', {
        description,
        top_k: topK,
        case_type: caseType,
      });
      return response.data;
    } catch (error) {
      console.error('判决预测失败:', error);
      throw error;
    }
  }

  async analyzeDispute(description) {
    try {
      const response = await this.client.post('/api/dispute-analysis', null, {
        params: { description },
      });
      return response.data;
    } catch (error) {
      console.error('争议焦点分析失败:', error);
      throw error;
    }
  }

  async generateDocument(description, docType = '民事起诉状', topK = 5, caseType = null) {
    try {
      const response = await this.client.post('/api/generate-document', {
        description,
        doc_type: docType,
        top_k: topK,
        case_type: caseType,
      });
      return response.data;
    } catch (error) {
      console.error('文书生成失败:', error);
      throw error;
    }
  }

  async healthCheck() {
    try {
      const response = await this.client.get('/api/health');
      return response.data;
    } catch (error) {
      console.error('健康检查失败:', error);
      throw error;
    }
  }
}

export default ApiService;

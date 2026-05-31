import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

export const getTestCases = async () => {
  try {
    const response = await api.get('/test-cases');
    return response.data;
  } catch (error) {
    console.error('获取测试用例失败:', error);
    throw error;
  }
};

export const createTestCase = async (testCase) => {
  try {
    const response = await api.post('/test-cases', testCase);
    return response.data;
  } catch (error) {
    console.error('创建测试用例失败:', error);
    throw error;
  }
};

export const updateTestCase = async (id, testCase) => {
  try {
    const response = await api.put(`/test-cases/${id}`, testCase);
    return response.data;
  } catch (error) {
    console.error('更新测试用例失败:', error);
    throw error;
  }
};

export const deleteTestCase = async (id) => {
  try {
    const response = await api.delete(`/test-cases/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除测试用例失败:', error);
    throw error;
  }
};

export default api;

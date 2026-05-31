import axios from 'axios';
import type {
  TopologyData,
  TopologyStats,
  ServiceNodeDetail,
  GroupedTopologyData,
  TopologyGroup,
  ConsumerGroupNode,
  TraceInfo,
  TraceDetail,
  ImpactAnalysisResult,
  ChangePredictionResult
} from '../types';

const API_BASE = '/api/topology';

export const topologyApi = {
  getFullTopology: async (): Promise<TopologyData> => {
    const response = await axios.get(`${API_BASE}`);
    return response.data;
  },

  getGroupedTopology: async (): Promise<GroupedTopologyData> => {
    const response = await axios.get(`${API_BASE}/grouped`);
    return response.data;
  },

  getTopologyByNamespace: async (namespace: string): Promise<TopologyData> => {
    const response = await axios.get(`${API_BASE}/namespace/${namespace}`);
    return response.data;
  },

  getTopologyStats: async (): Promise<TopologyStats> => {
    const response = await axios.get(`${API_BASE}/stats`);
    return response.data;
  },

  getServiceDetail: async (id: string): Promise<ServiceNodeDetail> => {
    const response = await axios.get(`${API_BASE}/services/${id}`);
    return response.data;
  },

  getAllGroups: async (): Promise<TopologyGroup[]> => {
    const response = await axios.get(`${API_BASE}/groups`);
    return response.data;
  },

  createGroup: async (group: Partial<TopologyGroup>): Promise<TopologyGroup> => {
    const response = await axios.post(`${API_BASE}/groups`, group);
    return response.data;
  },

  updateGroupCollapsed: async (groupId: string, collapsed: boolean) => {
    return axios.put(`${API_BASE}/groups/${groupId}/collapsed?collapsed=${collapsed}`);
  },

  deleteGroup: async (groupId: string) => {
    return axios.delete(`${API_BASE}/groups/${groupId}`);
  },

  addServiceToGroup: async (groupId: string, serviceId: string) => {
    return axios.post(`${API_BASE}/groups/${groupId}/services/${serviceId}`);
  },

  removeServiceFromGroup: async (groupId: string, serviceId: string) => {
    return axios.delete(`${API_BASE}/groups/${groupId}/services/${serviceId}`);
  },

  getAllConsumerGroups: async (): Promise<ConsumerGroupNode[]> => {
    const response = await axios.get(`${API_BASE}/consumer-groups`);
    return response.data;
  },

  getRecentTraces: async (limit: number = 100): Promise<TraceInfo[]> => {
    const response = await axios.get(`${API_BASE}/traces?limit=${limit}`);
    return response.data;
  },

  getTraceDetail: async (traceId: string): Promise<TraceDetail> => {
    const response = await axios.get(`${API_BASE}/traces/${traceId}`);
    return response.data;
  },

  triggerDiscovery: async () => {
    return axios.post(`${API_BASE}/discovery/trigger`);
  },

  clearAllData: async () => {
    return axios.delete(`${API_BASE}/clear`);
  },

  recordCall: async (data: any) => {
    return axios.post(`${API_BASE}/call`, data);
  },

  analyzeTrace: async (data: any) => {
    return axios.post(`${API_BASE}/trace`, data);
  },

  healthCheck: async () => {
    return axios.get(`${API_BASE}/health`);
  },

  getImpactAnalysis: async (serviceId: string): Promise<ImpactAnalysisResult> => {
    const response = await axios.get(`${API_BASE}/impact/${serviceId}`);
    return response.data;
  },

  getChangePrediction: async (serviceId: string, changeType: string = 'code'): Promise<ChangePredictionResult> => {
    const response = await axios.get(`${API_BASE}/change-prediction/${serviceId}?changeType=${changeType}`);
    return response.data;
  }
};

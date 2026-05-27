const API_BASE = '/api';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const json = (await res.json()) as ApiResponse<T>;
  if (!json.success) throw new Error(json.error || 'API error');
  return json.data as T;
}

export const api = {
  getLatestBlocks: (count: number = 10) =>
    request<any[]>(`/blocks/latest?count=${count}`),

  getBlock: (number: number) =>
    request<any>(`/blocks/${number}`),

  getLatestTransactions: (count: number = 10) =>
    request<any[]>(`/transactions/latest?count=${count}`),

  getTransaction: (hash: string) =>
    request<any>(`/transactions/${hash}`),

  getBlockTransactions: (blockNumber: number) =>
    request<any[]>(`/blocks/${blockNumber}/transactions`),

  getAddress: (address: string) =>
    request<any>(`/address/${address}`),

  getAddressTransactions: (address: string, limit: number = 20) =>
    request<any[]>(`/address/${address}/transactions?limit=${limit}`),

  getAddressTokens: (address: string) =>
    request<any[]>(`/address/${address}/tokens`),

  getLatestGas: () =>
    request<any>('/gas/latest'),

  getGasHistory: (days: number = 7) =>
    request<any[]>(`/gas/history?days=${days}`),

  search: (query: string) =>
    request<any>(`/search?q=${encodeURIComponent(query)}`),

  getContract: (address: string) =>
    request<any>(`/contract/${address}`),

  verifyContract: (data: {
    address: string;
    source: string;
    compilerVersion?: string;
    name?: string;
    optimization?: boolean;
    runs?: number;
  }) =>
    request<any>('/contract/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  callContract: (address: string, data: {
    method: string;
    params?: any[];
    from?: string;
    value?: string;
  }) =>
    request<any>(`/contract/${address}/call`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  readContract: (address: string, data: {
    abi: string;
    method: string;
    params?: any[];
  }) =>
    request<any>(`/contract/${address}/read`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getContractEvents: (address: string, data: {
    abi: string;
    eventName?: string;
    fromBlock?: number | string;
  }) =>
    request<any>(`/contract/${address}/events`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  estimateGas: (address: string, data: {
    abi: string;
    method: string;
    params?: any[];
    from?: string;
    value?: string;
  }) =>
    request<any>(`/contract/${address}/estimate-gas`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getAddressNFTs: (address: string) =>
    request<any[]>(`/nft/address/${address}`),

  getCollectionInfo: (contractAddress: string) =>
    request<any>(`/nft/collection/${contractAddress}`),

  getChains: () =>
    request<any[]>('/chains'),

  getMultiChainAddress: (address: string) =>
    request<any[]>(`/multichain/address/${address}`),

  getChainBlock: (chainId: string, blockNumber: number | 'latest') =>
    request<any>(`/multichain/${chainId}/block/${blockNumber}`),
};

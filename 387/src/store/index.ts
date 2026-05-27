import { create } from 'zustand';

interface SearchState {
  query: string;
  setQuery: (q: string) => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  setQuery: (q) => set({ query: q }),
}));

interface ContractState {
  verifiedContracts: Record<string, { verified: boolean; abi: string; name: string; source: string }>;
  setVerified: (address: string, data: { verified: boolean; abi: string; name: string; source: string }) => void;
}

export const useContractStore = create<ContractState>((set) => ({
  verifiedContracts: {},
  setVerified: (address, data) =>
    set((state) => ({
      verifiedContracts: { ...state.verifiedContracts, [address]: data },
    })),
}));

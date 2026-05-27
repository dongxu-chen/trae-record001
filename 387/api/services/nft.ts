import { web3 } from '../config/index.js';

interface NftAsset {
  contractAddress: string;
  tokenId: string;
  tokenType: 'ERC721' | 'ERC1155';
  name: string;
  symbol: string;
  tokenURI?: string;
  metadata?: Record<string, any>;
  balance?: string;
}

const NFT_COLLECTIONS = [
  {
    address: '0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D',
    name: 'Bored Ape YC',
    symbol: 'BAYC',
    type: 'ERC721' as const,
  },
  {
    address: '0x60E4d786628Fea6478F785A6d7e704777c86a7c6',
    name: 'Mutant Ape YC',
    symbol: 'MAYC',
    type: 'ERC721' as const,
  },
  {
    address: '0xED5AF388653567Af2F388E22ED6C02E5eE1376b6',
    name: 'Azuki',
    symbol: 'AZUKI',
    type: 'ERC721' as const,
  },
  {
    address: '0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B',
    name: 'CLONE X',
    symbol: 'CLONE',
    type: 'ERC721' as const,
  },
  {
    address: '0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e',
    name: 'Doodles',
    symbol: 'DOODLE',
    type: 'ERC721' as const,
  },
];

const ERC721_ABI = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'owner', type: 'address' }], outputs: [{ name: 'balance', type: 'uint256' }] },
  { name: 'tokenOfOwnerByIndex', type: 'function', inputs: [{ name: 'owner', type: 'address' }, { name: 'index', type: 'uint256' }], outputs: [{ name: 'tokenId', type: 'uint256' }] },
  { name: 'tokenURI', type: 'function', inputs: [{ name: 'tokenId', type: 'uint256' }], outputs: [{ name: '', type: 'string' }] },
  { name: 'name', type: 'function', inputs: [], outputs: [{ name: '', type: 'string' }] },
  { name: 'symbol', type: 'function', inputs: [], outputs: [{ name: '', type: 'string' }] },
];

const ERC1155_ABI = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }, { name: 'id', type: 'uint256' }], outputs: [{ name: '', type: 'uint256' }] },
  { name: 'balanceOfBatch', type: 'function', inputs: [{ name: 'accounts', type: 'address[]' }, { name: 'ids', type: 'uint256[]' }], outputs: [{ name: '', type: 'uint256[]' }] },
  { name: 'uri', type: 'function', inputs: [{ name: 'id', type: 'uint256' }], outputs: [{ name: '', type: 'string' }] },
];

export async function getAddressNFTs(address: string): Promise<NftAsset[]> {
  const nfts: NftAsset[] = [];

  for (const collection of NFT_COLLECTIONS) {
    try {
      const contract = new web3.eth.Contract(ERC721_ABI as any, collection.address);
      const balance = await contract.methods.balanceOf(address).call();
      const balanceNum = Number(balance);

      if (balanceNum > 0) {
        const [name, symbol] = await Promise.all([
          contract.methods.name().call().catch(() => collection.name),
          contract.methods.symbol().call().catch(() => collection.symbol),
        ]);

        const maxTokens = Math.min(balanceNum, 20);
        for (let i = 0; i < maxTokens; i++) {
          try {
            const tokenId = await contract.methods.tokenOfOwnerByIndex(address, i).call();
            const tokenURI = await contract.methods.tokenURI(tokenId).call().catch(() => undefined);

            nfts.push({
              contractAddress: collection.address,
              tokenId: tokenId.toString(),
              tokenType: 'ERC721',
              name: name as string,
              symbol: symbol as string,
              tokenURI: tokenURI as string | undefined,
            });
          } catch {
            continue;
          }
        }
      }
    } catch {
      continue;
    }
  }

  return nfts;
}

export async function getCollectionInfo(contractAddress: string): Promise<{
  name: string;
  symbol: string;
  totalSupply: string;
  tokenType: string;
} | null> {
  try {
    const contract = new web3.eth.Contract(ERC721_ABI as any, contractAddress);
    const [name, symbol] = await Promise.all([
      contract.methods.name().call(),
      contract.methods.symbol().call(),
    ]);

    return {
      name: name as string,
      symbol: symbol as string,
      totalSupply: '0',
      tokenType: 'ERC721',
    };
  } catch {
    return null;
  }
}

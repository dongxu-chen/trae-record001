import type { ChainProof, SignatureData, LegalDeclaration } from '../types';

const LEGAL_STATEMENT = `
法律声明

本人确认并声明：
1. 此电子签名为本人真实意愿表示，具有法律效力；
2. 本人确认所签署内容的真实性、合法性和完整性；
3. 本人同意本电子签名可作为法律证据使用；
4. 本人了解并承担签署本文件的所有法律后果；
5. 签名数据已进行哈希存证，可用于事后验证。

根据《中华人民共和国电子签名法》，可靠的电子签名与手写签名或者盖章具有同等的法律效力。
`;

class BlockchainSimulator {
  private chain: ChainProof[] = [];
  private pendingTransactions: Array<{ data: string; timestamp: number }> = [];
  private difficulty = 2;

  constructor() {
    this.createGenesisBlock();
  }

  private createGenesisBlock() {
    const genesisBlock: ChainProof = {
      hash: this.calculateHash('0', 'genesis', 0),
      previousHash: '0',
      timestamp: Date.now(),
      merkleRoot: 'genesis',
      nonce: 0,
      blockHeight: 0,
      transactionId: 'genesis',
    };
    this.chain.push(genesisBlock);
  }

  private calculateHash(previousHash: string, merkleRoot: string, nonce: number): string {
    const data = previousHash + merkleRoot + nonce;
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      hash = ((hash << 5) - hash + data.charCodeAt(i)) | 0;
    }
    return Math.abs(hash).toString(16).padStart(64, '0');
  }

  private proofOfWork(previousHash: string, merkleRoot: string): number {
    let nonce = 0;
    while (true) {
      const hash = this.calculateHash(previousHash, merkleRoot, nonce);
      if (hash.startsWith('0'.repeat(this.difficulty))) {
        return nonce;
      }
      nonce++;
    }
  }

  private calculateMerkleRoot(transactions: string[]): string {
    if (transactions.length === 0) return '0';
    if (transactions.length === 1) return this.sha256(transactions[0]);

    const newLevel: string[] = [];
    for (let i = 0; i < transactions.length; i += 2) {
      const left = transactions[i];
      const right = i + 1 < transactions.length ? transactions[i + 1] : left;
      newLevel.push(this.sha256(left + right));
    }
    return this.calculateMerkleRoot(newLevel);
  }

  private sha256(data: string): string {
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash + char) | 0;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(64, '0');
  }

  public addTransaction(data: string, timestamp: number): string {
    const txId = this.sha256(data + timestamp);
    this.pendingTransactions.push({ data, timestamp });
    return txId;
  }

  public mineBlock(): ChainProof | null {
    if (this.pendingTransactions.length === 0) return null;

    const lastBlock = this.chain[this.chain.length - 1];
    const merkleRoot = this.calculateMerkleRoot(
      this.pendingTransactions.map((t) => t.data)
    );
    const nonce = this.proofOfWork(lastBlock.hash, merkleRoot);
    const hash = this.calculateHash(lastBlock.hash, merkleRoot, nonce);

    const newBlock: ChainProof = {
      hash,
      previousHash: lastBlock.hash,
      timestamp: Date.now(),
      merkleRoot,
      nonce,
      blockHeight: this.chain.length,
      transactionId: this.pendingTransactions[0].data.substring(0, 64),
    };

    this.chain.push(newBlock);
    this.pendingTransactions = [];
    return newBlock;
  }

  public getLastBlock(): ChainProof {
    return this.chain[this.chain.length - 1];
  }

  public verifyChain(): boolean {
    for (let i = 1; i < this.chain.length; i++) {
      const current = this.chain[i];
      const previous = this.chain[i - 1];

      const validHash = this.calculateHash(
        current.previousHash,
        current.merkleRoot,
        current.nonce
      );
      if (current.hash !== validHash) return false;
      if (current.previousHash !== previous.hash) return false;
    }
    return true;
  }
}

const blockchain = new BlockchainSimulator();

export const generateSignatureHash = (signature: SignatureData): string => {
  const data = JSON.stringify({
    strokes: signature.strokes,
    signerId: signature.signerId,
    signerName: signature.signerName,
    createdAt: signature.createdAt,
  });

  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    const char = data.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0;
    hash = hash & hash;
  }
  return '0x' + Math.abs(hash).toString(16).padStart(64, '0');
};

export const createLegalDeclaration = (
  agreed: boolean,
  customStatement?: string
): LegalDeclaration => {
  return {
    agreed,
    agreedAt: Date.now(),
    statement: customStatement || LEGAL_STATEMENT.trim(),
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
  };
};

export const submitToBlockchain = async (
  signature: SignatureData
): Promise<ChainProof | null> => {
  try {
    const hash = generateSignatureHash(signature);
    const txData = JSON.stringify({
      hash,
      signerId: signature.signerId,
      signerName: signature.signerName,
      timestamp: signature.createdAt,
    });

    blockchain.addTransaction(txData, signature.createdAt);
    const proof = blockchain.mineBlock();

    return proof;
  } catch (error) {
    console.error('Failed to submit to blockchain:', error);
    return null;
  }
};

export const verifySignatureProof = (
  signature: SignatureData,
  proof: ChainProof
): boolean => {
  const hash = generateSignatureHash(signature);
  const txData = JSON.stringify({
    hash,
    signerId: signature.signerId,
    signerName: signature.signerName,
    timestamp: signature.createdAt,
  });

  return (
    proof.hash === signature.proof?.hash &&
    proof.transactionId.includes(txData.substring(0, 32))
  );
};

export const getLegalStatement = (): string => {
  return LEGAL_STATEMENT.trim();
};

export const formatHashForDisplay = (hash: string, length: number = 16): string => {
  if (hash.length <= length) return hash;
  const prefix = Math.floor(length / 2) - 2;
  const suffix = length - prefix - 3;
  return hash.substring(0, prefix) + '...' + hash.substring(hash.length - suffix);
};

export const getBlockchainStatus = (): {
  blockHeight: number;
  isVerified: boolean;
  lastHash: string;
} => {
  return {
    blockHeight: blockchain.getLastBlock().blockHeight,
    isVerified: blockchain.verifyChain(),
    lastHash: blockchain.getLastBlock().hash,
  };
};

export interface Point {
  x: number;
  y: number;
  pressure: number;
  time: number;
}

export interface SignatureStroke {
  points: Point[];
  color: string;
  width: number;
}

export interface SignatureData {
  id: string;
  strokes: SignatureStroke[];
  signerId: string;
  signerName: string;
  createdAt: number;
  imageData?: string;
  templateId?: string;
  hash?: string;
  proof?: ChainProof;
  legalDeclaration?: LegalDeclaration;
}

export interface Signer {
  id: string;
  name: string;
  credentialId?: string;
  publicKey?: string;
  credentialIdSecondary?: string;
  publicKeySecondary?: string;
  verificationLevel: 'none' | 'single' | 'dual';
  signatures: string[];
}

export interface SignatureVerificationResult {
  isVerified: boolean;
  similarity: number;
  details: {
    strokeCountMatch: boolean;
    averageSimilarity: number;
    boundingBoxSimilarity: number;
  };
}

export interface WebAuthnRegistration {
  credentialId: string;
  publicKey: string;
}

export interface SignatureTemplate {
  id: string;
  name: string;
  strokes: SignatureStroke[];
  imageData: string;
  signerId: string;
  createdAt: number;
  usageCount: number;
  lastUsedAt?: number;
}

export interface LegalDeclaration {
  agreed: boolean;
  agreedAt: number;
  statement: string;
  signerIp?: string;
  userAgent?: string;
}

export interface ChainProof {
  hash: string;
  previousHash: string;
  timestamp: number;
  merkleRoot: string;
  nonce: number;
  blockHeight: number;
  transactionId: string;
}

export interface BiometricVerificationResult {
  primaryVerified: boolean;
  secondaryVerified?: boolean;
  verificationLevel: 'none' | 'single' | 'dual';
  verifiedAt: number;
  method: 'fingerprint' | 'face' | 'device' | 'unknown';
}

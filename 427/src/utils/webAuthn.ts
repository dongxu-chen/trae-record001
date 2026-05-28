import type { WebAuthnRegistration, BiometricVerificationResult } from '../types';

export const isWebAuthnSupported = (): boolean => {
  return typeof window !== 'undefined' &&
         'PublicKeyCredential' in window &&
         typeof navigator.credentials !== 'undefined' &&
         typeof navigator.credentials.create === 'function' &&
         typeof navigator.credentials.get === 'function';
};

export const isUserVerifyingPlatformAuthenticatorAvailable = async (): Promise<boolean> => {
  if (!isWebAuthnSupported()) return false;
  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
};

const base64URLStringToBuffer = (base64URLString: string): ArrayBuffer => {
  const base64 = base64URLString.replace(/-/g, '+').replace(/_/g, '/');
  const padLength = (4 - (base64.length % 4)) % 4;
  const padded = base64.padEnd(base64.length + padLength, '=');
  const binary = atob(padded);
  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return buffer;
};

const bufferToBase64URLString = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
};

export type BiometricType = 'fingerprint' | 'face' | 'device';

export const registerWebAuthn = async (
  username: string,
  biometricType: BiometricType = 'device'
): Promise<WebAuthnRegistration | null> => {
  if (!isWebAuthnSupported()) {
    throw new Error('WebAuthn is not supported in this browser');
  }

  try {
    const authenticatorSelection: AuthenticatorSelectionCriteria = {
      userVerification: 'required',
      authenticatorAttachment: 'platform',
      residentKey: 'preferred',
    };

    const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
      challenge: crypto.getRandomValues(new Uint8Array(32)),
      rp: {
        name: 'SignaturePad WebApp',
        id: window.location.hostname,
      },
      user: {
        id: new TextEncoder().encode(`${username}_${biometricType}_${Date.now()}`),
        name: `${username} (${biometricType})`,
        displayName: `${username} - ${biometricType === 'fingerprint' ? '指纹' : biometricType === 'face' ? '人脸' : '设备'}认证`,
      },
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },
        { type: 'public-key', alg: -257 },
        { type: 'public-key', alg: -8 },
      ],
      authenticatorSelection,
      timeout: 120000,
      attestation: 'direct',
    };

    const credential = await navigator.credentials.create({
      publicKey: publicKeyCredentialCreationOptions,
    }) as PublicKeyCredential;

    if (!credential) {
      return null;
    }

    const response = credential.response as AuthenticatorAttestationResponse;
    const credentialId = bufferToBase64URLString(credential.rawId);
    const publicKey = response.attestationObject
      ? bufferToBase64URLString(response.attestationObject)
      : '';

    return {
      credentialId,
      publicKey,
    };
  } catch (error) {
    console.error('WebAuthn registration failed:', error);
    return null;
  }
};

export const authenticateWebAuthn = async (
  credentialId: string,
  requireUserVerification: boolean = true
): Promise<boolean> => {
  if (!isWebAuthnSupported()) {
    throw new Error('WebAuthn is not supported in this browser');
  }

  try {
    const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
      challenge: crypto.getRandomValues(new Uint8Array(32)),
      allowCredentials: [
        {
          id: base64URLStringToBuffer(credentialId),
          type: 'public-key',
          transports: ['internal', 'usb', 'nfc', 'ble'],
        },
      ],
      userVerification: requireUserVerification ? 'required' : 'preferred',
      timeout: 120000,
    };

    const assertion = await navigator.credentials.get({
      publicKey: publicKeyCredentialRequestOptions,
    }) as PublicKeyCredential;

    return !!assertion;
  } catch (error) {
    console.error('WebAuthn authentication failed:', error);
    return false;
  }
};

export const performDualFactorAuthentication = async (
  primaryCredentialId: string,
  secondaryCredentialId?: string
): Promise<BiometricVerificationResult> => {
  const result: BiometricVerificationResult = {
    primaryVerified: false,
    verificationLevel: 'none',
    verifiedAt: Date.now(),
    method: 'unknown',
  };

  try {
    result.primaryVerified = await authenticateWebAuthn(primaryCredentialId, true);
    result.method = 'fingerprint';

    if (result.primaryVerified && secondaryCredentialId) {
      result.secondaryVerified = await authenticateWebAuthn(secondaryCredentialId, true);
      result.verificationLevel = result.secondaryVerified ? 'dual' : 'single';
    } else if (result.primaryVerified) {
      result.verificationLevel = 'single';
    }

    return result;
  } catch (error) {
    console.error('Dual factor authentication failed:', error);
    return result;
  }
};

export const registerDualFactor = async (
  username: string
): Promise<{
  primary: WebAuthnRegistration | null;
  secondary: WebAuthnRegistration | null;
}> => {
  const primary = await registerWebAuthn(username, 'fingerprint');
  let secondary: WebAuthnRegistration | null = null;

  if (primary) {
    try {
      secondary = await registerWebAuthn(username, 'face');
    } catch {
      console.log('Secondary biometric registration skipped');
    }
  }

  return { primary, secondary };
};

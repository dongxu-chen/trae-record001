import axios from 'axios';
import type { VerifyResponse, VerifyOptions, SupportedFormat, TrustedCertificate, ComplianceCheck, BatchVerifyResponse } from '../../shared';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

export const verificationApi = {
  async uploadAndVerify(file: File, options: VerifyOptions): Promise<VerifyResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('verifyLevel', options.verifyLevel);
    formData.append('complianceStandard', options.complianceStandard);
    formData.append('checkRevocation', String(options.checkRevocation));
    formData.append('checkTimestamp', String(options.checkTimestamp));
    
    if (options.customTrustCerts) {
      options.customTrustCerts.forEach((cert, index) => {
        formData.append(`customTrustCerts[${index}]`, cert);
      });
    }

    const response = await apiClient.post('/verify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.data;
  },

  async batchVerify(files: File[], options: VerifyOptions): Promise<BatchVerifyResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('verifyLevel', options.verifyLevel);
    formData.append('complianceStandard', options.complianceStandard);
    formData.append('checkRevocation', String(options.checkRevocation));
    formData.append('checkTimestamp', String(options.checkTimestamp));

    const response = await apiClient.post('/verify/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.data;
  },

  async getBatchStatus(batchId: string): Promise<BatchVerifyResponse> {
    const response = await apiClient.get(`/verify/batch/${batchId}`);
    return response.data.data;
  },

  async getVerificationById(id: string): Promise<VerifyResponse> {
    const response = await apiClient.get(`/verify/${id}`);
    return response.data.data;
  },

  async getAllVerifications(): Promise<VerifyResponse[]> {
    const response = await apiClient.get('/verify');
    return response.data.data;
  },
};

export const reportApi = {
  async getHTMLReport(id: string): Promise<string> {
    const response = await apiClient.get(`/report/${id}/html`, {
      responseType: 'text',
    });
    return response.data;
  },

  async downloadPDFReport(id: string): Promise<void> {
    const response = await apiClient.get(`/report/${id}/pdf`, {
      responseType: 'blob',
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `verification-report-${id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export const certificateApi = {
  async getTrustedCertificates(): Promise<TrustedCertificate[]> {
    const response = await apiClient.get<TrustedCertificate[]>('/certificates/trusted');
    return response.data;
  },
};

export const complianceApi = {
  async getComplianceRules(): Promise<Record<string, ComplianceCheck[]>> {
    const response = await apiClient.get<Record<string, ComplianceCheck[]>>('/compliance/rules');
    return response.data;
  },

  async getComplianceStandards(): Promise<{ id: string; name: string; description: string }[]> {
    const response = await apiClient.get<{ id: string; name: string; description: string }[]>('/compliance/standards');
    return response.data;
  },
};

export const formatsApi = {
  async getSupportedFormats(): Promise<SupportedFormat[]> {
    return [
      {
        id: 'pades',
        name: 'PAdES',
        description: 'PDF Advanced Electronic Signatures，基于PDF的高级电子签名标准',
        extensions: ['.pdf'],
      },
      {
        id: 'xades',
        name: 'XAdES',
        description: 'XML Advanced Electronic Signatures，基于XML的高级电子签名标准',
        extensions: ['.xml', '.xades'],
      },
      {
        id: 'cades',
        name: 'CAdES',
        description: 'CMS Advanced Electronic Signatures，基于CMS/PKCS#7的高级电子签名标准',
        extensions: ['.p7s', '.pkcs7', '.p7m', '.der', '.pem'],
      },
    ];
  },
};

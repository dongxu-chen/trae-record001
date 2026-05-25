import type { QRFormData, QRCodeType } from '@/types';
import { formatVCard } from './vCard';
import { formatWiFi } from './wifiFormat';
import { formatEmail } from './emailFormat';

export function generateContent(formData: QRFormData): string {
  const { type, text, url, vcard, wifi, email } = formData;
  
  switch (type) {
    case 'text':
      return text || '';
    case 'url':
      return url || '';
    case 'vcard':
      return formatVCard(vcard);
    case 'wifi':
      return formatWiFi(wifi);
    case 'email':
      return formatEmail(email);
    default:
      return '';
  }
}

export function getTypeLabel(type: QRCodeType): string {
  const labels: Record<QRCodeType, string> = {
    text: '文本',
    url: '网址',
    vcard: '名片',
    wifi: 'WiFi',
    email: '邮件',
  };
  return labels[type];
}

import type { VCardData } from '@/types';

export function formatVCard(data: VCardData): string {
  const lines = ['BEGIN:VCARD', 'VERSION:3.0'];
  
  if (data.firstName || data.lastName) {
    lines.push(`N:${data.lastName};${data.firstName};;;`);
    lines.push(`FN:${data.firstName} ${data.lastName}`.trim());
  }
  if (data.organization) lines.push(`ORG:${data.organization}`);
  if (data.title) lines.push(`TITLE:${data.title}`);
  if (data.phone) lines.push(`TEL;TYPE=CELL:${data.phone}`);
  if (data.email) lines.push(`EMAIL:${data.email}`);
  if (data.website) lines.push(`URL:${data.website}`);
  if (data.address) lines.push(`ADR:;;${data.address};;;`);
  
  lines.push('END:VCARD');
  return lines.join('\n');
}

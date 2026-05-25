import type { EmailData } from '@/types';

export function formatEmail(data: EmailData): string {
  const params = new URLSearchParams();
  if (data.subject) params.set('subject', data.subject);
  if (data.body) params.set('body', data.body);
  
  const queryStr = params.toString();
  return `mailto:${data.to}${queryStr ? `?${queryStr}` : ''}`;
}

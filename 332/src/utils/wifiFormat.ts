import type { WiFiData } from '@/types';

export function formatWiFi(data: WiFiData): string {
  const { ssid, password, encryption, hidden } = data;
  const hiddenStr = hidden ? 'true' : 'false';
  const escape = (str: string): string => {
    return str.replace(/([\\:;,\\"])/g, '\\\\$1');
  };
  
  if (encryption === 'nopass') {
    return `WIFI:T:nopass;S:${escape(ssid)};H:${hiddenStr};;`;
  }
  return `WIFI:T:${encryption};S:${escape(ssid)};P:${escape(password)};H:${hiddenStr};;`;
}

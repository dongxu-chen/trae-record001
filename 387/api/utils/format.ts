export function formatAddress(address: string, startChars: number = 6, endChars: number = 4): string {
  if (!address) return '';
  if (address.length <= startChars + endChars + 2) return address;
  return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
}

export function formatHash(hash: string, startChars: number = 10, endChars: number = 8): string {
  if (!hash) return '';
  if (hash.length <= startChars + endChars + 2) return hash;
  return `${hash.slice(0, startChars)}...${hash.slice(-endChars)}`;
}

export function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatTimeAgo(timestamp: number): string {
  const now = Date.now() / 1000;
  const diff = now - timestamp;

  if (diff < 60) return `${Math.floor(diff)} 秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}

export function formatWeiToEth(wei: string | number | bigint): string {
  const value = typeof wei === 'bigint' ? wei : BigInt(wei || '0');
  const ether = Number(value) / 1e18;
  if (ether < 0.000001 && ether > 0) return '< 0.000001 ETH';
  return ether.toFixed(6) + ' ETH';
}

export function formatWeiToGwei(wei: string | number | bigint): string {
  const value = typeof wei === 'bigint' ? wei : BigInt(wei || '0');
  const gwei = Number(value) / 1e9;
  return gwei.toFixed(2) + ' Gwei';
}

export function formatNumber(num: string | number): string {
  const n = typeof num === 'string' ? Number(num) : num;
  return n.toLocaleString('zh-CN');
}

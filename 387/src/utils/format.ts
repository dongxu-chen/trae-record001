export function formatAddress(address: string, start: number = 6, end: number = 4): string {
  if (!address) return '';
  if (address.length <= start + end + 2) return address;
  return `${address.slice(0, start)}...${address.slice(-end)}`;
}

export function formatHash(hash: string, start: number = 10, end: number = 8): string {
  if (!hash) return '';
  if (hash.length <= start + end + 2) return hash;
  return `${hash.slice(0, start)}...${hash.slice(-end)}`;
}

export function formatTimestamp(timestamp: number): string {
  if (!timestamp) return '';
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
  if (!timestamp) return '';
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
  if (ether === 0) return '0 ETH';
  if (ether < 0.000001) return '< 0.000001 ETH';
  return ether.toFixed(6) + ' ETH';
}

export function formatWeiToGwei(wei: string | number | bigint): string {
  const value = typeof wei === 'bigint' ? wei : BigInt(wei || '0');
  const gwei = Number(value) / 1e9;
  return gwei.toFixed(2) + ' Gwei';
}

export function formatNumber(num: string | number): string {
  const n = typeof num === 'string' ? Number(num) : num;
  if (isNaN(n)) return '0';
  return n.toLocaleString('zh-CN');
}

export function formatGasUsedPercent(gasUsed: string, gasLimit: string): string {
  const used = Number(gasUsed);
  const limit = Number(gasLimit);
  if (limit === 0) return '0%';
  return ((used / limit) * 100).toFixed(2) + '%';
}

export function shortenText(text: string, maxLength: number = 50): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

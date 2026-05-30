const SHORT_CODE_STORAGE_KEY = 'chart_drill_short_codes';

interface ShortCodeMap {
  [shortCode: string]: string;
}

interface ReverseMap {
  [fullPath: string]: string;
}

let shortCodeCache: ShortCodeMap = {};
let reverseCache: ReverseMap = {};
let codeCounter = 100;

function loadCache(): void {
  try {
    const stored = localStorage.getItem(SHORT_CODE_STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      shortCodeCache = data.shortCodes || {};
      reverseCache = data.reverse || {};
      codeCounter = data.counter || 100;
    }
  } catch {
    shortCodeCache = {};
    reverseCache = {};
    codeCounter = 100;
  }
}

function saveCache(): void {
  try {
    localStorage.setItem(SHORT_CODE_STORAGE_KEY, JSON.stringify({
      shortCodes: shortCodeCache,
      reverse: reverseCache,
      counter: codeCounter,
    }));
  } catch {
  }
}

function generateShortCode(): string {
  codeCounter++;
  return codeCounter.toString(36);
}

export function compressPath(fullPath: string): string {
  loadCache();

  if (reverseCache[fullPath]) {
    return reverseCache[fullPath];
  }

  const shortCode = generateShortCode();
  shortCodeCache[shortCode] = fullPath;
  reverseCache[fullPath] = shortCode;
  saveCache();

  return shortCode;
}

export function decompressPath(shortCode: string): string | null {
  loadCache();
  return shortCodeCache[shortCode] || null;
}

export function encodeDrillState(path: string[], chartType: string): string {
  const pathStr = path.join(',');
  const stateStr = `${pathStr}|${chartType}`;
  return compressPath(stateStr);
}

export function decodeDrillState(shortCode: string): { path: string[]; chartType: string } | null {
  const decoded = decompressPath(shortCode);
  if (!decoded) return null;

  const [pathStr, chartType] = decoded.split('|');
  return {
    path: pathStr ? pathStr.split(',') : [],
    chartType: (chartType as 'bar' | 'pie' | 'line') || 'bar',
  };
}

export function clearExpiredCodes(maxAge: number = 7 * 24 * 60 * 60 * 1000): void {
  loadCache();

  const now = Date.now();
  const stored = localStorage.getItem(SHORT_CODE_STORAGE_KEY);
  let lastCleanup = 0;

  if (stored) {
    try {
      const data = JSON.parse(stored);
      lastCleanup = data.lastCleanup || 0;
    } catch {
    }
  }

  if (now - lastCleanup < maxAge) return;

  const allCodes = Object.keys(shortCodeCache);
  if (allCodes.length > 100) {
    const toRemove = allCodes.slice(0, allCodes.length - 50);
    toRemove.forEach((code) => {
      const fullPath = shortCodeCache[code];
      delete shortCodeCache[code];
      if (fullPath) delete reverseCache[fullPath];
    });
  }

  try {
    localStorage.setItem(SHORT_CODE_STORAGE_KEY, JSON.stringify({
      shortCodes: shortCodeCache,
      reverse: reverseCache,
      counter: codeCounter,
      lastCleanup: now,
    }));
  } catch {
  }
}

export function getShortCodeStats(): { total: number; cacheSize: number } {
  loadCache();
  return {
    total: Object.keys(shortCodeCache).length,
    cacheSize: new Blob([JSON.stringify(shortCodeCache)]).size,
  };
}

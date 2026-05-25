export const VIDEO_CONSTRAINTS = {
  '360p': { width: { ideal: 640 }, height: { ideal: 360 } },
  '480p': { width: { ideal: 854 }, height: { ideal: 480 } },
  '720p': { width: { ideal: 1280 }, height: { ideal: 720 } },
  '1080p': { width: { ideal: 1920 }, height: { ideal: 1080 } }
};

export const AUDIO_CONSTRAINTS = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  sampleRate: 48000,
  sampleSize: 16,
  channelCount: 1
};

export const RESOLUTION_LEVELS = [
  { name: '360p', width: 640, height: 360, bitrate: 500 },
  { name: '480p', width: 854, height: 480, bitrate: 1000 },
  { name: '720p', width: 1280, height: 720, bitrate: 2500 },
  { name: '1080p', width: 1920, height: 1080, bitrate: 4000 }
];

export const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
    { urls: 'stun:stun3.l.google.com:19302' },
    { urls: 'stun:stun4.l.google.com:19302' }
  ]
};

export const PEER_CONFIG = {
  ...ICE_SERVERS,
  trickle: true,
  offerOptions: {
    offerToReceiveAudio: true,
    offerToReceiveVideo: true
  }
};

export const BANDWIDTH_THRESHOLDS = {
  poor: 300,
  fair: 800,
  good: 2000,
  excellent: 4000
};

export const SCREEN_SHARE_CONSTRAINTS = {
  video: {
    cursor: 'always',
    displaySurface: 'monitor'
  },
  audio: {
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false
  }
};

export const RECORDING_CONFIG = {
  mimeType: 'video/webm;codecs=vp9,opus',
  videoBitsPerSecond: 2500000,
  audioBitsPerSecond: 128000
};

export const VIRTUAL_BACKGROUNDS = [
  { id: 'none', name: '无', type: 'none' },
  { id: 'blur', name: '模糊', type: 'blur' },
  { id: 'office', name: '办公室', type: 'color', color: '#2563eb' },
  { id: 'nature', name: '自然', type: 'gradient', colors: ['#22c55e', '#15803d'] },
  { id: 'sunset', name: '日落', type: 'gradient', colors: ['#f97316', '#dc2626'] },
  { id: 'ocean', name: '海洋', type: 'gradient', colors: ['#0ea5e9', '#0284c7'] },
  { id: 'purple', name: '紫色', type: 'gradient', colors: ['#8b5cf6', '#6d28d9'] }
];

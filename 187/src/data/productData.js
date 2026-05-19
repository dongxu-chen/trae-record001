export const productInfo = {
  id: 1001,
  title: 'Apple iPhone 15 Pro Max 256GB 钛金属',
  subtitle: 'A17 Pro芯片 | 钛金属设计 | 4800万像素主摄',
  brand: 'Apple',
  sales: 12580,
  rating: 4.9,
  reviewCount: 3256,
  shipping: '顺丰包邮 · 48小时内发货',
  services: ['7天无理由退换', '正品保障', '全国联保', '分期免息'],
  description: `全新钛金属设计，搭载 A17 Pro 芯片，性能再攀高峰。
4800万像素主摄，支持 5 倍光学变焦。
USB-C 接口，支持 USB 3.0 速度，传输更高效。
全天候电池续航，最长可达 29 小时视频播放。
灵动岛功能，让通知和实时活动一目了然。`
}

export const specGroups = [
  {
    id: 'color',
    name: '颜色',
    options: [
      { id: 'natural', name: '原色钛金属', value: '#D3D3D3' },
      { id: 'blue', name: '蓝色钛金属', value: '#4A90D9' },
      { id: 'white', name: '白色钛金属', value: '#F5F5F5' },
      { id: 'black', name: '黑色钛金属', value: '#2C2C2E' }
    ]
  },
  {
    id: 'storage',
    name: '存储容量',
    options: [
      { id: '256', name: '256GB', value: '256GB' },
      { id: '512', name: '512GB', value: '512GB' },
      { id: '1t', name: '1TB', value: '1TB' }
    ]
  }
]

export const skuList = [
  { id: 'sku001', specs: { color: 'natural', storage: '256' }, price: 9999, originalPrice: 10999, stock: 128, images: [1, 2, 3, 4] },
  { id: 'sku002', specs: { color: 'natural', storage: '512' }, price: 11999, originalPrice: 12999, stock: 86, images: [1, 2, 3, 4] },
  { id: 'sku003', specs: { color: 'natural', storage: '1t' }, price: 13999, originalPrice: 14999, stock: 42, images: [1, 2, 3, 4] },
  { id: 'sku004', specs: { color: 'blue', storage: '256' }, price: 9999, originalPrice: 10999, stock: 156, images: [5, 6, 7, 8] },
  { id: 'sku005', specs: { color: 'blue', storage: '512' }, price: 11999, originalPrice: 12999, stock: 98, images: [5, 6, 7, 8] },
  { id: 'sku006', specs: { color: 'blue', storage: '1t' }, price: 13999, originalPrice: 14999, stock: 35, images: [5, 6, 7, 8] },
  { id: 'sku007', specs: { color: 'white', storage: '256' }, price: 9999, originalPrice: 10999, stock: 210, images: [9, 10, 11, 12] },
  { id: 'sku008', specs: { color: 'white', storage: '512' }, price: 11999, originalPrice: 12999, stock: 145, images: [9, 10, 11, 12] },
  { id: 'sku009', specs: { color: 'white', storage: '1t' }, price: 13999, originalPrice: 14999, stock: 68, images: [9, 10, 11, 12] },
  { id: 'sku010', specs: { color: 'black', storage: '256' }, price: 9999, originalPrice: 10999, stock: 188, images: [13, 14, 15, 16] },
  { id: 'sku011', specs: { color: 'black', storage: '512' }, price: 11999, originalPrice: 12999, stock: 112, images: [13, 14, 15, 16] },
  { id: 'sku012', specs: { color: 'black', storage: '1t' }, price: 13999, originalPrice: 14999, stock: 56, images: [13, 14, 15, 16] }
]

export const productImages = {
  1: 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=800&h=800&fit=crop',
  2: 'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=800&h=800&fit=crop',
  3: 'https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=800&h=800&fit=crop',
  4: 'https://images.unsplash.com/photo-1580910051074-3eb694886505?w=800&h=800&fit=crop',
  5: 'https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=800&h=800&fit=crop',
  6: 'https://images.unsplash.com/photo-1512054502232-10a0a035d672?w=800&h=800&fit=crop',
  7: 'https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=800&h=800&fit=crop',
  8: 'https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=800&h=800&fit=crop',
  9: 'https://images.unsplash.com/photo-1575153113404-a566e7dd4c0b?w=800&h=800&fit=crop',
  10: 'https://images.unsplash.com/photo-1606041008023-472dfb5e530f?w=800&h=800&fit=crop',
  11: 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=800&h=800&fit=crop',
  12: 'https://images.unsplash.com/photo-1605108615741-001409a3e9a3?w=800&h=800&fit=crop',
  13: 'https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=800&h=800&fit=crop',
  14: 'https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=800&h=800&fit=crop',
  15: 'https://images.unsplash.com/photo-1597773150803-35bf40f4a752?w=800&h=800&fit=crop',
  16: 'https://images.unsplash.com/photo-1580319922807-4141e7a9d404?w=800&h=800&fit=crop'
}

export const reviews = [
  {
    id: 1,
    userName: '数码爱好者',
    avatar: 'https://i.pravatar.cc/100?img=1',
    rating: 5,
    date: '2024-01-15',
    specs: '原色钛金属 / 256GB',
    content: '钛金属手感真的很棒，比上一代轻了很多。A17 Pro 性能没得说，游戏画质拉满也不卡顿。相机拍照效果非常惊艳，尤其是夜景模式。',
    images: [
      'https://images.unsplash.com/photo-1512054502232-10a0a035d672?w=200&h=200&fit=crop',
      'https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=200&h=200&fit=crop'
    ],
    helpful: 256
  },
  {
    id: 2,
    userName: '摄影小白',
    avatar: 'https://i.pravatar.cc/100?img=2',
    rating: 5,
    date: '2024-01-12',
    specs: '蓝色钛金属 / 512GB',
    content: '作为摄影爱好者，4800万像素主摄太香了！细节保留非常好，后期裁切空间很大。蓝色钛金属真的太好看了，低调又有质感。',
    images: [
      'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=200&h=200&fit=crop'
    ],
    helpful: 189
  },
  {
    id: 3,
    userName: '果粉一枚',
    avatar: 'https://i.pravatar.cc/100?img=3',
    rating: 4,
    date: '2024-01-10',
    specs: '白色钛金属 / 256GB',
    content: '从 iPhone 13 Pro 升级上来，提升很明显。续航比之前好太多了，一天完全没问题。唯一不足就是价格有点贵，但一分钱一分货。',
    images: [],
    helpful: 98
  },
  {
    id: 4,
    userName: '程序员小王',
    avatar: 'https://i.pravatar.cc/100?img=4',
    rating: 5,
    date: '2024-01-08',
    specs: '黑色钛金属 / 1TB',
    content: '1TB 版本存储自由了，再也不用天天删照片。USB 3.0 传输速度真的快，大文件备份节省很多时间。黑色非常商务，适合办公用。',
    images: [
      'https://images.unsplash.com/photo-1580910051074-3eb694886505?w=200&h=200&fit=crop',
      'https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=200&h=200&fit=crop',
      'https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=200&h=200&fit=crop'
    ],
    helpful: 342
  },
  {
    id: 5,
    userName: '学生党小李',
    avatar: 'https://i.pravatar.cc/100?img=5',
    rating: 5,
    date: '2024-01-05',
    specs: '原色钛金属 / 256GB',
    content: '用了教育优惠入手的，性价比很高。游戏体验超棒，原神全高画质稳定60帧。灵动岛看球赛实时比分太方便了！',
    images: [],
    helpful: 156
  },
  {
    id: 6,
    userName: '时尚达人',
    avatar: 'https://i.pravatar.cc/100?img=6',
    rating: 5,
    date: '2024-01-03',
    specs: '蓝色钛金属 / 256GB',
    content: '蓝色真的太好看了！拿在手里质感满满，拍照发朋友圈大家都问是什么手机。续航也很给力，重度使用一天没问题。',
    images: [
      'https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=200&h=200&fit=crop'
    ],
    helpful: 203
  },
  {
    id: 7,
    userName: '商务人士张先生',
    avatar: 'https://i.pravatar.cc/100?img=7',
    rating: 4,
    date: '2024-01-01',
    specs: '黑色钛金属 / 512GB',
    content: '商务用很合适，黑色低调沉稳。邮件处理、视频会议都很流畅。就是充电速度还是不如安卓旗舰，希望下一代能改进。',
    images: [],
    helpful: 87
  },
  {
    id: 8,
    userName: '旅行博主小美',
    avatar: 'https://i.pravatar.cc/100?img=8',
    rating: 5,
    date: '2023-12-28',
    specs: '白色钛金属 / 512GB',
    content: '旅行拍照神器！4800万像素拍风景太赞了，白天夜晚都很出色。轻便易携带，视频录制也很稳，vlog 必备。',
    images: [
      'https://images.unsplash.com/photo-1575153113404-a566e7dd4c0b?w=200&h=200&fit=crop',
      'https://images.unsplash.com/photo-1606041008023-472dfb5e530f?w=200&h=200&fit=crop'
    ],
    helpful: 421
  },
  {
    id: 9,
    userName: '游戏玩家阿强',
    avatar: 'https://i.pravatar.cc/100?img=9',
    rating: 5,
    date: '2023-12-25',
    specs: '原色钛金属 / 1TB',
    content: 'A17 Pro 游戏性能爆表！原神、星穹铁道全高画质满帧运行。1TB 装了20多个游戏还剩一半空间，太爽了！',
    images: [],
    helpful: 298
  },
  {
    id: 10,
    userName: '评测达人',
    avatar: 'https://i.pravatar.cc/100?img=10',
    rating: 4,
    date: '2023-12-20',
    specs: '蓝色钛金属 / 1TB',
    content: '综合体验最好的 iPhone。钛金属重量控制优秀，单手操作无压力。影像系统第一梯队，视频录制无人能敌。',
    images: [
      'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=200&h=200&fit=crop'
    ],
    helpful: 567
  }
]

export const productVideo = {
  id: 'video001',
  title: 'iPhone 15 Pro Max 深度评测',
  duration: '08:32',
  thumbnail: 'https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=800&h=450&fit=crop',
  videoUrl: 'https://www.w3schools.com/html/mov_bbb.mp4'
}

export const relatedProducts = [
  {
    id: 2001,
    title: 'Apple AirPods Pro 2',
    price: 1899,
    originalPrice: 1999,
    image: 'https://images.unsplash.com/photo-1606220838315-056192d5e927?w=400&h=400&fit=crop',
    sales: 8956,
    rating: 4.8,
    matchRate: 95
  },
  {
    id: 2002,
    title: 'Apple Watch Ultra 2',
    price: 6499,
    originalPrice: 6999,
    image: 'https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop',
    sales: 5623,
    rating: 4.9,
    matchRate: 92
  },
  {
    id: 2003,
    title: 'MagSafe 充电器',
    price: 329,
    originalPrice: 399,
    image: 'https://images.unsplash.com/photo-1556656793-08538906a9f8?w=400&h=400&fit=crop',
    sales: 15680,
    rating: 4.7,
    matchRate: 88
  },
  {
    id: 2004,
    title: 'Apple Leather Case',
    price: 459,
    originalPrice: 499,
    image: 'https://images.unsplash.com/photo-1601593346740-925612772716?w=400&h=400&fit=crop',
    sales: 23456,
    rating: 4.6,
    matchRate: 85
  },
  {
    id: 2005,
    title: '20W USB-C 充电器',
    price: 149,
    originalPrice: 199,
    image: 'https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400&h=400&fit=crop',
    sales: 45678,
    rating: 4.8,
    matchRate: 90
  },
  {
    id: 2006,
    title: 'Apple Pencil (USB-C)',
    price: 799,
    originalPrice: 899,
    image: 'https://images.unsplash.com/photo-1591445408159-2fa167f4ca89?w=400&h=400&fit=crop',
    sales: 12345,
    rating: 4.7,
    matchRate: 78
  }
]

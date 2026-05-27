import moment from 'moment';

const generateMockEvents = () => {
  const events = [];
  const tracks = [
    { id: 'track1', name: '项目', color: '#3b82f6' },
    { id: 'track2', name: '研发', color: '#10b981' },
    { id: 'track3', name: '运营', color: '#f59e0b' }
  ];

  const eventTypes = [
    { type: '会议', color: '#3b82f6' },
    { type: '培训', color: '#10b981' },
    { type: '评审', color: '#8b5cf6' },
    { type: '发布', color: '#22c55e' },
    { type: '团建', color: '#ec4899' },
    { type: '调研', color: '#f97316' },
    { type: '维护', color: '#06b6d4' }
  ];

  const locations = [
    '上海国际会议中心',
    '公司会议室A',
    '公司会议室B',
    '公司大会议室',
    '线上会议',
    '客户公司',
    '杭州',
    '北京',
    '多个地点',
    '多个城市',
    '三亚',
    '上海',
    '公司'
  ];

  for (let i = 1; i <= 50; i++) {
    const startDate = moment('2024-01-01').add(Math.floor(Math.random() * 180), 'days');
    const duration = Math.floor(Math.random() * 5) + 1;
    const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const track = tracks[Math.floor(Math.random() * tracks.length)];
    const location = locations[Math.floor(Math.random() * locations.length)];
    const participants = Math.floor(Math.random() * 50) + 5;
    const statuses = ['已完成', '进行中', '计划中'];
    const status = statuses[Math.floor(Math.random() * statuses.length)];

    const endDate = startDate.clone().add(duration, 'days');
    events.push({
      id: `event-${i}`,
      title: `${eventType.type}${i}`,
      startTime: startDate.valueOf(),
      endTime: endDate.valueOf(),
      trackId: track.id,
      type: 'event',
      color: eventType.color,
      description: `${eventType.type}活动描述信息，这是一个关于${eventType.type}的详细描述，包含了活动的目的、内容和预期效果的详细说明。`,
      details: {
        location: location,
        participants: participants,
        status: status,
        organizer: ['张三', '李四', '王五'][Math.floor(Math.random() * 3)],
        category: eventType.type
      }
    });
  }

  return events;
};

const tracks = [
  { id: 'track1', name: '项目', color: '#3b82f6' },
  { id: 'track2', name: '研发', color: '#10b981' },
  { id: 'track3', name: '运营', color: '#f59e0b' }
];

export { generateMockEvents, tracks };

const { Client } = require('@elastic/elasticsearch');

const client = new Client({
  node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
});

const VIDEO_INDEX = 'videos';
const USER_INTERACTIONS_INDEX = 'user_interactions';

async function initializeIndices() {
  const videoIndexExists = await client.indices.exists({ index: VIDEO_INDEX });
  if (!videoIndexExists.body) {
    await client.indices.create({
      index: VIDEO_INDEX,
      settings: {
        analysis: {
          analyzer: {
            autocomplete: {
              type: 'custom',
              tokenizer: 'autocomplete',
              filter: ['lowercase'],
            },
            autocomplete_search: {
              type: 'custom',
              tokenizer: 'standard',
              filter: ['lowercase'],
            },
          },
          tokenizer: {
            autocomplete: {
              type: 'edge_ngram',
              min_gram: 1,
              max_gram: 20,
              token_chars: ['letter', 'digit'],
            },
          },
        },
      },
      mappings: {
        properties: {
          id: { type: 'keyword' },
          title: {
            type: 'text',
            analyzer: 'autocomplete',
            search_analyzer: 'autocomplete_search',
            fields: {
              keyword: {
                type: 'keyword',
                ignore_above: 256,
              },
            },
          },
          description: {
            type: 'text',
            analyzer: 'standard',
            fields: {
              keyword: {
                type: 'keyword',
                ignore_above: 256,
              },
            },
          },
          videoUrl: { type: 'keyword' },
          thumbnailUrl: { type: 'keyword' },
          author: { type: 'keyword' },
          authorId: { type: 'keyword' },
          categories: { type: 'keyword' },
          tags: { type: 'keyword' },
          duration: { type: 'integer' },
          views: { type: 'integer' },
          likes: { type: 'integer' },
          comments: { type: 'integer' },
          shares: { type: 'integer' },
          createdAt: { type: 'date' },
          trendingScore: { type: 'float' },
          freshScore: { type: 'float' },
        },
      },
    });
  }

  const interactionIndexExists = await client.indices.exists({
    index: USER_INTERACTIONS_INDEX,
  });
  if (!interactionIndexExists.body) {
    await client.indices.create({
      index: USER_INTERACTIONS_INDEX,
      mappings: {
        properties: {
          userId: { type: 'keyword' },
          videoId: { type: 'keyword' },
          interactionType: { type: 'keyword' },
          timestamp: { type: 'date' },
          durationWatched: { type: 'float' },
        },
      },
    });
  }
}

async function searchVideos({
  userId,
  excludedVideoIds = [],
  limit = 10,
  userPreferences = [],
}) {
  const shouldClauses = [];

  if (userPreferences.length > 0) {
    shouldClauses.push({
      terms: {
        categories: userPreferences,
        boost: 2.0,
      },
    });
  }

  shouldClauses.push({
    function_score: {
      functions: [
        {
          field_value_factor: {
            field: 'trendingScore',
            factor: 1,
            modifier: 'log1p',
          },
          weight: 2.0,
        },
        {
          field_value_factor: {
            field: 'freshScore',
            factor: 1,
          },
          weight: 1.5,
        },
        {
          gauss: {
            createdAt: {
              origin: 'now',
              scale: '7d',
              decay: 0.5,
            },
          },
          weight: 1.0,
        },
      ],
      score_mode: 'sum',
    },
  });

  const query = {
    bool: {
      must_not: excludedVideoIds.length > 0 ? [
        {
          terms: {
            id: excludedVideoIds,
          },
        },
      ] : [],
      should: shouldClauses,
      minimum_should_match: 1,
    },
  };

  const result = await client.search({
    index: VIDEO_INDEX,
    query,
    size: limit,
    sort: [{ _score: { order: 'desc' } }],
  });

  return result.hits.hits.map((hit) => ({
    id: hit._source.id,
    ...hit._source,
    score: hit._score,
  }));
}

async function recordInteraction({
  userId,
  videoId,
  interactionType,
  durationWatched = 0,
}) {
  await client.index({
    index: USER_INTERACTIONS_INDEX,
    document: {
      userId,
      videoId,
      interactionType,
      timestamp: new Date(),
      durationWatched,
    },
    refresh: true,
  });

  const updates = {};

  if (interactionType === 'like') {
    updates.likes = { increment: 1 };
  } else if (interactionType === 'comment') {
    updates.comments = { increment: 1 };
  } else if (interactionType === 'share') {
    updates.shares = { increment: 1 };
  } else if (interactionType === 'view') {
    updates.views = { increment: 1 };
  }

  if (Object.keys(updates).length > 0) {
    await client.update({
      index: VIDEO_INDEX,
      id: videoId,
      script: {
        source: Object.entries(updates)
          .map(([field, op]) => `ctx._source.${field} ${op.increment ? '+=' + op.increment : ''}`)
          .join('; '),
      },
    });
  }
}

async function getUserPreferences(userId) {
  const result = await client.search({
    index: USER_INTERACTIONS_INDEX,
    query: {
      bool: {
        must: [
          { term: { userId } },
          {
            terms: {
              interactionType: ['like', 'complete_watch', 'share'],
            },
          },
        ],
      },
    },
    aggs: {
      byVideo: {
        terms: {
          field: 'videoId',
          size: 50,
        },
      },
    },
    size: 0,
  });

  const videoIds = result.aggregations.byVideo.buckets.map((b) => b.key);

  if (videoIds.length === 0) {
    return [];
  }

  const videoResult = await client.search({
    index: VIDEO_INDEX,
    query: {
      ids: {
        values: videoIds,
      },
    },
    aggs: {
      topCategories: {
        terms: {
          field: 'categories',
          size: 10,
        },
      },
    },
    size: 0,
  });

  return videoResult.aggregations.topCategories.buckets.map((b) => b.key);
}

async function insertSampleVideos() {
  const sampleVideos = [
    {
      id: 'video1',
      title: 'Amazing Travel Tips You Need to Know',
      description: 'Essential travel hacks for your next adventure',
      videoUrl: 'https://example.com/video1.mp4',
      thumbnailUrl: 'https://example.com/thumb1.jpg',
      author: 'TravelExplorer',
      authorId: 'user1',
      categories: ['travel', 'lifestyle'],
      tags: ['travel', 'tips', 'vacation'],
      duration: 30,
      views: 15000,
      likes: 2300,
      comments: 150,
      shares: 500,
      createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      trendingScore: 4.5,
      freshScore: 4.2,
    },
    {
      id: 'video2',
      title: 'Quick and Easy Cooking Recipe',
      description: '5-minute recipe for busy days',
      videoUrl: 'https://example.com/video2.mp4',
      thumbnailUrl: 'https://example.com/thumb2.jpg',
      author: 'ChefMaster',
      authorId: 'user2',
      categories: ['food', 'cooking'],
      tags: ['recipe', 'quick', 'food'],
      duration: 45,
      views: 25000,
      likes: 4500,
      comments: 300,
      shares: 800,
      createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      trendingScore: 5.0,
      freshScore: 4.8,
    },
    {
      id: 'video3',
      title: 'Fitness Workout at Home',
      description: 'No equipment needed - 15 minute full body workout',
      videoUrl: 'https://example.com/video3.mp4',
      thumbnailUrl: 'https://example.com/thumb3.jpg',
      author: 'FitLife',
      authorId: 'user3',
      categories: ['fitness', 'health'],
      tags: ['workout', 'fitness', 'home'],
      duration: 900,
      views: 10000,
      likes: 1800,
      comments: 100,
      shares: 350,
      createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      trendingScore: 3.8,
      freshScore: 3.5,
    },
    {
      id: 'video4',
      title: 'Funny Pet Compilation',
      description: 'Hilarious moments with cats and dogs',
      videoUrl: 'https://example.com/video4.mp4',
      thumbnailUrl: 'https://example.com/thumb4.jpg',
      author: 'PetLovers',
      authorId: 'user4',
      categories: ['comedy', 'pets'],
      tags: ['pets', 'funny', 'cats'],
      duration: 120,
      views: 50000,
      likes: 8500,
      comments: 600,
      shares: 2000,
      createdAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
      trendingScore: 4.9,
      freshScore: 4.9,
    },
    {
      id: 'video5',
      title: 'Learn JavaScript in 10 Minutes',
      description: 'Crash course for beginners',
      videoUrl: 'https://example.com/video5.mp4',
      thumbnailUrl: 'https://example.com/thumb5.jpg',
      author: 'CodeMaster',
      authorId: 'user5',
      categories: ['education', 'technology'],
      tags: ['javascript', 'coding', 'learn'],
      duration: 600,
      views: 30000,
      likes: 5200,
      comments: 400,
      shares: 1200,
      createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      trendingScore: 4.2,
      freshScore: 3.0,
    },
    {
      id: 'video6',
      title: 'Daily Vlog - City Life',
      description: 'A day in my life in the city',
      videoUrl: 'https://example.com/video6.mp4',
      thumbnailUrl: 'https://example.com/thumb6.jpg',
      author: 'DailyVlogger',
      authorId: 'user6',
      categories: ['vlog', 'lifestyle'],
      tags: ['vlog', 'daily', 'city'],
      duration: 180,
      views: 8000,
      likes: 1200,
      comments: 80,
      shares: 200,
      createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
      trendingScore: 3.5,
      freshScore: 4.5,
    },
    {
      id: 'video7',
      title: 'DIY Home Decor Ideas',
      description: 'Budget-friendly decoration tips',
      videoUrl: 'https://example.com/video7.mp4',
      thumbnailUrl: 'https://example.com/thumb7.jpg',
      author: 'HomeDesign',
      authorId: 'user7',
      categories: ['lifestyle', 'diy'],
      tags: ['diy', 'home', 'decor'],
      duration: 240,
      views: 12000,
      likes: 2100,
      comments: 180,
      shares: 600,
      createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      trendingScore: 4.0,
      freshScore: 4.2,
    },
    {
      id: 'video8',
      title: 'Music Cover Performance',
      description: 'Amazing cover of a popular song',
      videoUrl: 'https://example.com/video8.mp4',
      thumbnailUrl: 'https://example.com/thumb8.jpg',
      author: 'MusicStar',
      authorId: 'user8',
      categories: ['music', 'entertainment'],
      tags: ['music', 'cover', 'song'],
      duration: 150,
      views: 40000,
      likes: 7000,
      comments: 500,
      shares: 1500,
      createdAt: new Date(Date.now() - 18 * 60 * 60 * 1000),
      trendingScore: 4.7,
      freshScore: 4.6,
    },
  ];

  for (const video of sampleVideos) {
    await client.update({
      index: VIDEO_INDEX,
      id: video.id,
      script: {
        source: 'ctx._source = params.video',
        params: { video },
      },
      upsert: video,
    });
  }

  await client.indices.refresh({ index: VIDEO_INDEX });
}

async function fuzzySearchVideos({
  query,
  excludedVideoIds = [],
  limit = 10,
}) {
  const mustClauses = [
    {
      bool: {
        should: [
          {
            match: {
              title: {
                query,
                analyzer: 'autocomplete_search',
                boost: 3.0,
              },
            },
          },
          {
            match: {
              description: {
                query,
                fuzziness: 'AUTO',
              },
            },
          },
          {
            terms: {
              tags: {
                value: query.toLowerCase(),
              },
            },
          },
          {
            wildcard: {
              title: {
                value: `*${query.toLowerCase()}*`,
              },
            },
          },
        ],
        minimum_should_match: 1,
      },
    },
  ];

  const searchQuery = {
    bool: {
      must: mustClauses,
      must_not: excludedVideoIds.length > 0 ? [
        {
          terms: {
            id: excludedVideoIds,
          },
        },
      ] : [],
    },
  };

  const result = await client.search({
    index: VIDEO_INDEX,
    query: searchQuery,
    size: limit,
    sort: [{ _score: { order: 'desc' } }],
  });

  return result.hits.hits.map((hit) => ({
    id: hit._source.id,
    ...hit._source,
    score: hit._score,
  }));
}

module.exports = {
  client,
  initializeIndices,
  searchVideos,
  fuzzySearchVideos,
  recordInteraction,
  getUserPreferences,
  insertSampleVideos,
  VIDEO_INDEX,
  USER_INTERACTIONS_INDEX,
};

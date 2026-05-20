import type { VueQueryPluginOptions } from '@tanstack/vue-query'

export const vueQueryConfig: VueQueryPluginOptions = {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        cacheTime: 10 * 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
      mutations: {
        retry: 0,
      },
    },
  },
}

export const queryKeys = {
  articles: {
    all: ['articles'] as const,
    lists: (filters: { category?: string | null; tag?: string | null; page?: number }) => [
      ...queryKeys.articles.all,
      'list',
      filters,
    ] as const,
    detail: (id: number) => [...queryKeys.articles.all, 'detail', id] as const,
  },
  categories: {
    all: ['categories'] as const,
  },
  tags: {
    all: ['tags'] as const,
  },
} as const

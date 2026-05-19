import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref } from 'vue'
import {
  fetchArticles,
  fetchArticleById,
  fetchCategories,
  fetchTags,
  type ArticleListParams,
} from '../api/articles'
import { queryKeys } from '../config/vue-query'

export function useArticles(params: ArticleListParams) {
  return useQuery({
    queryKey: queryKeys.articles.lists({
      category: params.category,
      tag: params.tag,
      page: params.page,
    }),
    queryFn: () =>
      fetchArticles({
        category: params.category,
        tag: params.tag,
        page: params.page,
      }),
  })
}

export function useArticleDetail(id: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.articles.detail(id ?? 0),
    queryFn: () => (id ? fetchArticleById(id) : Promise.resolve(null)),
    enabled: !!id,
  })
}

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories.all,
    queryFn: fetchCategories,
    staleTime: 30 * 60 * 1000,
  })
}

export function useTags() {
  return useQuery({
    queryKey: queryKeys.tags.all,
    queryFn: fetchTags,
    staleTime: 30 * 60 * 1000,
  })
}

export function useArticlePrefetch() {
  const queryClient = useQueryClient()

  const prefetchArticle = (id: number) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.articles.detail(id),
      queryFn: () => fetchArticleById(id),
      staleTime: 5 * 60 * 1000,
    })
  }

  return { prefetchArticle }
}

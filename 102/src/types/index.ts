export interface Article {
  id: number
  title: string
  excerpt: string
  content: string
  category: string
  tags: string[]
  coverImage: string
  createdAt: string
  readTime: number
  author: string
}

export interface Category {
  name: string
  count: number
}

export interface Tag {
  name: string
  count: number
}

export interface FriendLink {
  id: number
  name: string
  url: string
  avatar: string
  description: string
}

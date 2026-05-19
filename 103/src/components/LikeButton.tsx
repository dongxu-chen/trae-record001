'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'

interface LikeButtonProps {
  snippetId: string
}

export default function LikeButton({ snippetId }: LikeButtonProps) {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [likesCount, setLikesCount] = useState(0)
  const [userLiked, setUserLiked] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const fetchLikes = async () => {
      try {
        const response = await fetch(`/api/snippets/${snippetId}/likes`)
        if (response.ok) {
          const data = await response.json()
          setLikesCount(data.count)
          setUserLiked(data.userLiked)
        }
      } catch (error) {
        console.error('Failed to fetch likes:', error)
      }
    }

    fetchLikes()
  }, [snippetId])

  const handleLike = async () => {
    if (status === 'unauthenticated') {
      router.push('/login')
      return
    }

    setIsLoading(true)
    try {
      const method = userLiked ? 'DELETE' : 'POST'
      const response = await fetch(`/api/snippets/${snippetId}/likes`, {
        method
      })

      if (response.ok) {
        setUserLiked(!userLiked)
        setLikesCount(prev => userLiked ? prev - 1 : prev + 1)
      }
    } catch (error) {
      console.error('Failed to like snippet:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <button
      onClick={handleLike}
      disabled={isLoading}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
        userLiked
          ? 'bg-red-500 text-white hover:bg-red-600'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      } disabled:opacity-50`}
    >
      <span>{userLiked ? '❤️' : '🤍'}</span>
      <span>{likesCount}</span>
    </button>
  )
}

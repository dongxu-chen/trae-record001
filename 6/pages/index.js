import Link from 'next/link'
import Head from 'next/head'
import { getPosts } from '../lib/api'

export async function getServerSideProps() {
  try {
    const posts = await getPosts()
    return {
      props: { posts }
    }
  } catch (error) {
    return {
      props: { posts: [], error: error.message }
    }
  }
}

function PostCard({ post }) {
  return (
    <article style={{
      padding: '20px',
      marginBottom: '20px',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      backgroundColor: 'white'
    }}>
      <Link href={`/post/${post.id}`} style={{ textDecoration: 'none' }}>
        <h2 style={{
          marginTop: 0,
          marginBottom: '8px',
          color: '#1f2937',
          cursor: 'pointer'
        }}>
          {post.title}
        </h2>
      </Link>
      <div style={{
        color: '#6b7280',
        fontSize: '14px',
        marginBottom: '12px'
      }}>
        作者：{post.author} · {new Date(post.createdAt).toLocaleDateString()}
      </div>
      <p style={{
        color: '#374151',
        margin: 0,
        lineHeight: '1.6'
      }}>
        {post.excerpt || (post.content ? post.content.substring(0, 200) + '...' : '')}
      </p>
      <Link href={`/post/${post.id}`} style={{
        display: 'inline-block',
        marginTop: '12px',
        color: '#2563eb',
        textDecoration: 'none'
      }}>
        阅读更多 →
      </Link>
    </article>
  )
}

export default function Home({ posts, error }) {
  return (
    <div style={{
      maxWidth: '800px',
      margin: '0 auto',
      padding: '20px'
    }}>
      <Head>
        <title>我的博客</title>
        <meta name="description" content="一个基于 Next.js SSR 的博客网站" />
      </Head>

      <header style={{ marginBottom: '40px' }}>
        <h1 style={{
          fontSize: '32px',
          marginBottom: '8px',
          color: '#1f2937'
        }}>
          我的博客
        </h1>
        <p style={{ color: '#6b7280', margin: 0 }}>
          分享技术与生活的点滴
        </p>
      </header>

      {error ? (
        <div style={{
          padding: '16px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '4px',
          color: '#dc2626'
        }}>
          加载失败：{error}
        </div>
      ) : posts.length === 0 ? (
        <p style={{ color: '#6b7280', textAlign: 'center', padding: '40px' }}>
          暂无文章
        </p>
      ) : (
        posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))
      )}
    </div>
  )
}

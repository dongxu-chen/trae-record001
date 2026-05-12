import Link from 'next/link'
import Head from 'next/head'
import { getPost, getComments } from '../../lib/api'
import Comments from '../../components/Comment'

export async function getStaticPaths() {
  return {
    paths: [],
    fallback: 'blocking'
  }
}

export async function getStaticProps(context) {
  const { id } = context.params

  try {
    const [post, comments] = await Promise.all([
      getPost(id),
      getComments(id)
    ])

    return {
      props: { post, comments },
      revalidate: 60
    }
  } catch (error) {
    const statusMatch = error.message && error.message.match(/^API call failed:\s*(\d{3})/)
    const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : null

    if (statusCode === 404) {
      return {
        notFound: true
      }
    }
    return {
      props: { post: null, comments: [], error: error.message },
      revalidate: 30
    }
  }
}

export default function PostDetail({ post, comments, error }) {
  if (!post) {
    return (
      <div style={{
        maxWidth: '800px',
        margin: '0 auto',
        padding: '40px 20px',
        textAlign: 'center'
      }}>
        <p style={{ color: '#dc2626', fontSize: '18px' }}>
          {error ? `加载失败：${error}` : '文章不存在'}
        </p>
        <Link href="/" style={{
          display: 'inline-block',
          marginTop: '20px',
          color: '#2563eb',
          textDecoration: 'none'
        }}>
          ← 返回首页
        </Link>
      </div>
    )
  }

  return (
    <div style={{
      maxWidth: '800px',
      margin: '0 auto',
      padding: '20px'
    }}>
      <Head>
        <title>{post.title} - 我的博客</title>
        <meta name="description" content={post.excerpt || post.content?.substring(0, 160)} />
      </Head>

      <Link href="/" style={{
        display: 'inline-block',
        marginBottom: '20px',
        color: '#2563eb',
        textDecoration: 'none'
      }}>
        ← 返回首页
      </Link>

      <article>
        <header style={{ marginBottom: '24px' }}>
          <h1 style={{
            fontSize: '32px',
            marginBottom: '12px',
            color: '#1f2937'
          }}>
            {post.title}
          </h1>
          <div style={{ color: '#6b7280', fontSize: '14px' }}>
            作者：{post.author} · {new Date(post.createdAt).toLocaleDateString()}
          </div>
        </header>

        <div style={{
          fontSize: '16px',
          lineHeight: '1.8',
          color: '#374151'
        }}>
          {post.content?.split('\n').map((paragraph, index) => (
            <p key={index} style={{ marginBottom: '16px' }}>
              {paragraph}
            </p>
          ))}
        </div>
      </article>

      <Comments postId={post.id} initialComments={comments} />
    </div>
  )
}

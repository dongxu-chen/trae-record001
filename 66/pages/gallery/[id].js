import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

export default function ImageDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (id) {
      fetchImage();
    }
  }, [id]);

  const fetchImage = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/images/${id}`);
      const data = await response.json();
      if (data.success) {
        setImage(data.image);
      } else {
        setError(data.error || '图片不存在');
      }
    } catch (err) {
      console.error('Failed to fetch image:', err);
      setError('加载图片失败');
    } finally {
      setLoading(false);
    }
  };

  const handleLike = async () => {
    try {
      const response = await fetch(`/api/images/${id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'like' }),
      });

      const data = await response.json();
      if (data.success) {
        setImage((prev) => ({ ...prev, likes: data.likes }));
      }
    } catch (err) {
      console.error('Like error:', err);
    }
  };

  const handleDelete = async () => {
    if (!confirm('确定要删除这张图片吗？此操作无法撤销。')) {
      return;
    }

    try {
      const response = await fetch(`/api/images/${id}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      if (data.success) {
        router.push('/');
      } else {
        alert('删除失败: ' + data.error);
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert('删除失败');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  if (error || !image) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
        <p className="text-red-500 text-xl mb-4">{error || '图片不存在'}</p>
        <Link href="/">
          <span className="text-blue-600 hover:underline">返回首页</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <Link href="/">
            <span className="text-blue-600 hover:underline">← 返回画廊</span>
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="bg-gray-100 flex items-center justify-center">
            <img
              src={image.cloudinaryUrl}
              alt={image.title}
              className="max-w-full max-h-[70vh] object-contain"
            />
          </div>

          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{image.title}</h1>
                <p className="text-sm text-gray-500 mt-1">
                  上传于{' '}
                  {new Date(image.createdAt).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleLike}
                  className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                >
                  ❤️ <span>{image.likes}</span>
                </button>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-red-100 hover:text-red-600 transition-colors"
                >
                  删除
                </button>
              </div>
            </div>

            {image.description && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  描述
                </h2>
                <p className="text-gray-700">{image.description}</p>
              </div>
            )}

            {image.tags && image.tags.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  标签
                </h2>
                <div className="flex flex-wrap gap-2">
                  {image.tags.map((tag, index) => (
                    <Link key={index} href={`/?tag=${tag}`}>
                      <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full hover:bg-blue-200 cursor-pointer">
                        #{tag}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{image.views}</div>
                <div className="text-sm text-gray-500">浏览次数</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{image.likes}</div>
                <div className="text-sm text-gray-500">喜欢</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {image.tags?.length || 0}
                </div>
                <div className="text-sm text-gray-500">标签</div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

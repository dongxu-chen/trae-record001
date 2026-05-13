import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import ImageCard from '../../components/ImageCard';

export default function UserGallery() {
  const router = useRouter();
  const { name } = router.query;
  const { data: session } = useSession();
  const [userImages, setUserImages] = useState([]);
  const [likedImages, setLikedImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('uploads');
  const [pagination, setPagination] = useState({
    hasNext: false,
    hasPrev: false,
    nextCursor: null,
    prevCursor: null,
    limit: 12,
  });

  const isOwnGallery = session?.user?.username === name;

  useEffect(() => {
    if (name && activeTab === 'uploads') {
      fetchUserImages();
    } else if (name && activeTab === 'likes' && session?.user?.id) {
      fetchLikedImages();
    }
  }, [name, activeTab, session]);

  const fetchUserImages = async (cursor = null, direction = 'next') => {
    if (!name) return;
    setLoading(true);
    try {
      let url = `/api/users/${name}/images?limit=${pagination.limit}`;
      if (cursor) {
        url += `&cursor=${encodeURIComponent(cursor)}&direction=${direction}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setUserImages(data.images);
        setPagination(data.pagination);
      }
    } catch (error) {
      console.error('Failed to fetch user images:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchLikedImages = async () => {
    if (!session?.user?.id || !isOwnGallery) {
      setLikedImages([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch('/api/users/me/likes');
      const data = await response.json();
      if (data.success) {
        setLikedImages(data.images);
      }
    } catch (error) {
      console.error('Failed to fetch liked images:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentImages = activeTab === 'uploads' ? userImages : likedImages;

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
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white text-3xl font-bold">
              {name?.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {name}
                {isOwnGallery && (
                  <span className="ml-2 text-sm font-normal text-blue-600">(我)</span>
                )}
              </h1>
              <p className="text-gray-500">
                {activeTab === 'uploads'
                  ? `上传了 ${userImages.length} 张图片`
                  : `喜欢了 ${likedImages.length} 张图片`}
              </p>
            </div>
          </div>

          {isOwnGallery && (
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setActiveTab('uploads')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'uploads'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                我的上传
              </button>
              <button
                onClick={() => setActiveTab('likes')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'likes'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                我喜欢的
              </button>
            </div>
          )}
        </div>

        <div>
          {loading ? (
            <div className="text-center py-12 text-gray-500">加载中...</div>
          ) : currentImages.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-500">
                {activeTab === 'uploads'
                  ? '暂无上传的图片'
                  : '暂无喜欢的图片'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {currentImages.map((image) => (
                <ImageCard key={image._id} image={image} />
              ))}
            </div>
          )}

          {activeTab === 'uploads' && (pagination.hasNext || pagination.hasPrev) && (
            <div className="flex justify-center gap-4 mt-8">
              <button
                onClick={() => fetchUserImages(pagination.prevCursor, 'prev')}
                disabled={!pagination.hasPrev}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  pagination.hasPrev
                    ? 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                ← 上一页
              </button>
              <button
                onClick={() => fetchUserImages()}
                className="px-6 py-2 rounded-lg font-medium bg-white text-gray-700 hover:bg-gray-100 border border-gray-300 transition-colors"
              >
                最新
              </button>
              <button
                onClick={() => fetchUserImages(pagination.nextCursor, 'next')}
                disabled={!pagination.hasNext}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  pagination.hasNext
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                下一页 →
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useSession, signIn, signOut } from 'next-auth/react';
import ImageCard from '../components/ImageCard';

export default function Home() {
  const { data: session, status } = useSession();
  const [images, setImages] = useState([]);
  const [trendingImages, setTrendingImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    tags: '',
    image: null,
  });
  const [pagination, setPagination] = useState({
    hasNext: false,
    hasPrev: false,
    nextCursor: null,
    prevCursor: null,
    firstCursor: null,
    lastCursor: null,
    limit: 12,
  });
  const xhrRef = useRef(null);

  useEffect(() => {
    fetchImages();
    fetchTrending();
  }, []);

  const fetchImages = async (cursor = null, direction = 'next') => {
    setLoading(true);
    try {
      let url = `/api/images?limit=${pagination.limit}`;
      if (cursor) {
        url += `&cursor=${encodeURIComponent(cursor)}&direction=${direction}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setImages(data.images);
        setPagination(data.pagination);
      }
    } catch (error) {
      console.error('Failed to fetch images:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrending = async () => {
    try {
      const response = await fetch('/api/trending');
      const data = await response.json();
      if (data.success) {
        setTrendingImages(data.images);
      }
    } catch (error) {
      console.error('Failed to fetch trending images:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setFormData((prev) => ({ ...prev, image: file }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.image) {
      alert('请选择一张图片');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadStage('准备上传...');

    const form = new FormData();
    form.append('image', formData.image);
    form.append('title', formData.title);
    form.append('description', formData.description);
    form.append('tags', formData.tags);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhrRef.current = xhr;

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 80);
          setUploadProgress(percent);
          setUploadStage('上传中...');
        }
      });

      xhr.addEventListener('load', () => {
        setUploadProgress(85);
        setUploadStage('处理中...');

        try {
          const data = JSON.parse(xhr.responseText);

          if (xhr.status >= 200 && xhr.status < 300 && data.success) {
            setUploadProgress(100);
            setUploadStage('完成！');
            setFormData({
              title: '',
              description: '',
              tags: '',
              image: null,
            });
            setTimeout(() => {
              fetchImages();
              alert('图片上传成功！');
              setUploading(false);
              setUploadProgress(0);
              setUploadStage('');
            }, 500);
            resolve(data);
          } else {
            setUploading(false);
            alert('上传失败: ' + (data.error || 'Unknown error'));
            reject(new Error(data.error || 'Upload failed'));
          }
        } catch (error) {
          setUploading(false);
          console.error('Parse error:', error);
          alert('上传失败');
          reject(error);
        }
      });

      xhr.addEventListener('error', () => {
        setUploading(false);
        console.error('XHR error');
        alert('上传失败');
        reject(new Error('Network error'));
      });

      xhr.addEventListener('abort', () => {
        setUploading(false);
        setUploadProgress(0);
        setUploadStage('');
        reject(new Error('Upload aborted'));
      });

      xhr.open('POST', '/api/upload', true);
      xhr.send(form);
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">图片画廊</h1>
            <p className="mt-2 text-gray-600">上传和分享你的精彩瞬间</p>
          </div>
          <div className="flex items-center gap-4">
            {session ? (
              <>
                <Link href={`/user/${session.user.username}`}>
                  <span className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 cursor-pointer">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                      {session.user.username.charAt(0).toUpperCase()}
                    </div>
                    <span className="font-medium">{session.user.name}</span>
                  </span>
                </Link>
                <button
                  onClick={() => signOut()}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  退出登录
                </button>
              </>
            ) : (
              <button
                onClick={() => signIn()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                登录 / 注册
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {trendingImages.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">🔥 热门图片</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
              {trendingImages.slice(0, 5).map((image) => (
                <Link key={image._id} href={`/gallery/${image._id}`}>
                  <div className="aspect-square overflow-hidden rounded-lg cursor-pointer hover:opacity-90">
                    <img
                      src={image.cloudinaryUrl}
                      alt={image.title}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <p className="text-sm text-gray-600 mt-2 truncate">{image.title}</p>
                  <p className="text-xs text-gray-400">❤️ {image.likes}</p>
                </Link>
              ))}
            </div>
          </div>
        )}

        {session ? (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">上传新图片</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                标题 *
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="给图片起个名字"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                描述
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="添加一些描述..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                标签 (用逗号分隔)
              </label>
              <input
                type="text"
                name="tags"
                value={formData.tags}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="例如: 风景, 旅行, 美食"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择图片 *
              </label>
              <input
                type="file"
                name="image"
                accept="image/*"
                onChange={handleFileChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>{uploadStage}</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-blue-600 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={uploading}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              {uploading ? '上传中...' : '上传图片'}
            </button>
          </form>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md p-8 mb-8 text-center">
            <div className="text-6xl mb-4">📷</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">上传你的第一张图片</h2>
            <p className="text-gray-500 mb-6">登录后即可上传和管理你的图片画廊</p>
            <button
              onClick={() => signIn()}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              立即登录
            </button>
          </div>
        )}

        <div>
          <h2 className="text-xl font-semibold mb-4 text-gray-800">浏览图片</h2>
          {loading ? (
            <div className="text-center py-12 text-gray-500">加载中...</div>
          ) : images.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-500">暂无图片，快来上传第一张吧！</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {images.map((image) => (
                <ImageCard key={image._id} image={image} />
              ))}
            </div>
          )}

          {(pagination.hasNext || pagination.hasPrev) && (
            <div className="flex justify-center gap-4 mt-8">
              <button
                onClick={() => fetchImages(pagination.prevCursor, 'prev')}
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
                onClick={() => fetchImages()}
                className="px-6 py-2 rounded-lg font-medium bg-white text-gray-700 hover:bg-gray-100 border border-gray-300 transition-colors"
              >
                首页
              </button>
              <button
                onClick={() => fetchImages(pagination.nextCursor, 'next')}
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

      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500">
          <p>图片画廊 - 由 Next.js + Cloudinary + MongoDB 驱动</p>
        </div>
      </footer>
    </div>
  );
}

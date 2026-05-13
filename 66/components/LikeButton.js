import { useState, useEffect } from 'react';

const LikeButton = ({ imageId, initialLikes = 0, initialLiked = false }) => {
  const [likes, setLikes] = useState(initialLikes);
  const [liked, setLiked] = useState(initialLiked);
  const [loading, setLoading] = useState(false);

  const handleLike = async () => {
    if (loading) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/likes/${imageId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        setLikes(data.likes);
        setLiked(data.liked);
      } else if (data.redirect) {
        window.location.href = data.redirect;
      } else {
        alert(data.error || '操作失败');
      }
    } catch (error) {
      console.error('Like error:', error);
      alert('操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleLike}
      disabled={loading}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
        liked
          ? 'bg-red-50 text-red-600 hover:bg-red-100'
          : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      <span className={`text-xl transition-transform duration-200 ${liked ? 'scale-110' : ''}`}>
        {liked ? '❤️' : '🤍'}
      </span>
      <span>{likes}</span>
    </button>
  );
};

export default LikeButton;

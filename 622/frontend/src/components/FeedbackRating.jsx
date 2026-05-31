import React, { useState } from 'react';
import { submitFeedback } from '../services/api';

const FeedbackRating = ({ contentId, styleId, onRated }) => {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleRate = async (star) => {
    if (loading || submitted) return;
    
    setRating(star);
    setLoading(true);
    
    try {
      await submitFeedback({
        style_id: styleId,
        rating: star,
        content_id: contentId,
        user_id: 'default'
      });
      setSubmitted(true);
      if (onRated) onRated(star);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      setRating(0);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setRating(0);
    setHovered(0);
    setSubmitted(false);
  };

  const ratingLabels = ['很差', '较差', '一般', '较好', '很好'];

  return (
    <div className="flex flex-col items-center gap-2 py-3">
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => handleRate(star)}
            onMouseEnter={() => !submitted && setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            disabled={loading || submitted}
            className={`text-2xl transition-all duration-150 transform 
              ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer hover:scale-125'}
              ${submitted ? 'cursor-default' : ''}
            `}
          >
            <span
              className={`${
                (hovered || rating) >= star
                  ? 'text-yellow-400 drop-shadow-sm'
                  : 'text-gray-300'
              }`}
            >
              ★
            </span>
          </button>
        ))}
      </div>
      
      {loading && (
        <p className="text-xs text-blue-500">提交中...</p>
      )}
      
      {submitted && !loading && (
        <div className="flex items-center gap-2">
          <p className="text-xs text-green-600 font-medium">
            感谢您的反馈！({ratingLabels[rating - 1]})
          </p>
          <button
            onClick={reset}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            重新评分
          </button>
        </div>
      )}
      
      {!submitted && !loading && (hovered || rating) > 0 && (
        <p className="text-xs text-gray-500">{ratingLabels[(hovered || rating) - 1]}</p>
      )}
    </div>
  );
};

export default FeedbackRating;

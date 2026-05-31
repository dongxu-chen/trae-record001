function IntensitySlider({ intensity, onIntensityChange }) {
  const marks = [0, 25, 50, 75, 100];
  
  return (
    <div className="space-y-3">
      <div className="relative">
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={intensity}
          onChange={(e) => onIntensityChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-full appearance-none cursor-pointer slider-thumb"
          style={{
            background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${intensity * 100}%, #374151 ${intensity * 100}%, #374151 100%)`
          }}
        />
      </div>
      
      <div className="flex justify-between">
        {marks.map((mark) => (
          <button
            key={mark}
            onClick={() => onIntensityChange(mark / 100)}
            className={`text-xs transition-colors ${
              Math.abs(intensity * 100 - mark) < 5
                ? 'text-primary-400 font-medium'
                : 'text-gray-500 hover:text-gray-400'
            }`}
          >
            {mark}%
          </button>
        ))}
      </div>
      
      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>保留原图</span>
        <span>强风格化</span>
      </div>
    </div>
  );
}

export default IntensitySlider;

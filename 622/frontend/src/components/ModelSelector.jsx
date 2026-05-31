import { Zap, Sparkles, Clock, Info, Rocket } from 'lucide-react';

const models = [
  {
    id: 'sd_turbo',
    name: 'SD Turbo',
    description: '超高速风格迁移，<1秒推理',
    speed: '极速',
    quality: '优秀',
    icon: Rocket,
    color: 'from-accent-500 to-primary-500',
    recommended: true
  },
  {
    id: 'gan',
    name: 'GAN',
    description: '快速风格迁移',
    speed: '快速',
    quality: '良好',
    icon: Zap,
    color: 'from-blue-500 to-cyan-500'
  },
  {
    id: 'diffusion',
    name: 'Diffusion',
    description: '高质量生成',
    speed: '较慢',
    quality: '极佳',
    icon: Sparkles,
    color: 'from-purple-500 to-pink-500'
  }
];

function ModelSelector({ selectedModel, onModelChange }) {
  return (
    <div className="space-y-3">
      {models.map((model) => {
        const Icon = model.icon;
        const isSelected = selectedModel === model.id;
        
        return (
          <button
            key={model.id}
            onClick={() => onModelChange(model.id)}
            className={`w-full p-4 rounded-xl text-left transition-all ${
              isSelected
                ? 'bg-gradient-to-r ' + model.color + ' bg-opacity-20 ring-2 ring-primary-400'
                : 'bg-gray-800/50 hover:bg-gray-700/50'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center relative ${
                isSelected ? 'bg-white/20' : 'bg-gray-700'
              }`}>
                <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-gray-400'}`} />
                {model.recommended && (
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                    <span className="text-[8px] text-white font-bold">NEW</span>
                  </div>
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className={`font-semibold ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                    {model.name}
                  </h3>
                  {model.recommended && (
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                      推荐
                    </span>
                  )}
                </div>
                <p className={`text-sm ${isSelected ? 'text-white/70' : 'text-gray-500'}`}>
                  {model.description}
                </p>
                <div className="flex items-center gap-4 mt-2">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-400">{model.speed}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Info className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-400">质量: {model.quality}</span>
                  </div>
                </div>
              </div>
              {isSelected && (
                <div className="w-5 h-5 rounded-full bg-white/30 flex items-center justify-center">
                  <div className="w-3 h-3 rounded-full bg-white" />
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export default ModelSelector;

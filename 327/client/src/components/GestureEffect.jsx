import React, { useState, useEffect, useCallback } from 'react';

const gestureEffects = {
  hand_raise: {
    icon: '✋',
    color: 'from-yellow-400 to-orange-500',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/50',
    text: '举手发言',
    particles: 12,
    sound: null
  },
  thumbs_up: {
    icon: '👍',
    color: 'from-blue-400 to-cyan-500',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/50',
    text: '点赞',
    particles: 8,
    sound: null
  },
  peace: {
    icon: '✌️',
    color: 'from-purple-400 to-pink-500',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/50',
    text: '胜利',
    particles: 10,
    sound: null
  },
  love: {
    icon: '🤟',
    color: 'from-pink-400 to-red-500',
    bgColor: 'bg-pink-500/20',
    borderColor: 'border-pink-500/50',
    text: '爱你',
    particles: 15,
    sound: null
  },
  fist: {
    icon: '✊',
    color: 'from-red-400 to-orange-500',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/50',
    text: '加油',
    particles: 10,
    sound: null
  },
  open_palm: {
    icon: '🖐️',
    color: 'from-green-400 to-emerald-500',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/50',
    text: '你好',
    particles: 10,
    sound: null
  }
};

const Particle = ({ x, y, delay, color, size }) => {
  const angle = Math.random() * Math.PI * 2;
  const distance = 50 + Math.random() * 100;
  const endX = Math.cos(angle) * distance;
  const endY = Math.sin(angle) * distance;

  return (
    <div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: x,
        top: y,
        width: size,
        height: size,
        background: `linear-gradient(135deg, ${color})`,
        animation: `particle 1s ease-out ${delay}ms forwards`,
        '--tx': `${endX}px`,
        '--ty': `${endY}px`
      }}
    />
  );
};

const GestureEffect = ({ gesture, onComplete }) => {
  const [particles, setParticles] = useState([]);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!gesture) return;

    setVisible(true);
    
    const effect = gestureEffects[gesture.type] || gestureEffects.open_palm;
    const newParticles = [];
    
    for (let i = 0; i < effect.particles; i++) {
      newParticles.push({
        id: i,
        x: '50%',
        y: '50%',
        delay: i * 30,
        color: effect.color,
        size: 6 + Math.random() * 8
      });
    }
    
    setParticles(newParticles);

    const timer = setTimeout(() => {
      setVisible(false);
      setParticles([]);
      onComplete?.();
    }, 2000);

    return () => clearTimeout(timer);
  }, [gesture, onComplete]);

  if (!visible || !gesture) return null;

  const effect = gestureEffects[gesture.type] || gestureEffects.open_palm;

  return (
    <div className="fixed inset-0 pointer-events-none z-50 flex items-center justify-center">
      <div className="relative">
        <div 
          className={`text-8xl animate-bounce mb-4 ${effect.bgColor} p-8 rounded-full border-2 ${effect.borderColor}`}
          style={{
            animation: 'gesturePop 0.5s ease-out'
          }}
        >
          {effect.icon}
        </div>
        
        <div 
          className="absolute -bottom-12 left-1/2 -translate-x-1/2 text-2xl font-bold text-white whitespace-nowrap"
          style={{
            textShadow: '0 2px 10px rgba(0,0,0,0.5)',
            animation: 'textSlideUp 0.5s ease-out'
          }}
        >
          {effect.text}！
        </div>

        {particles.map(p => (
          <Particle key={p.id} {...p} />
        ))}
      </div>

      <div 
        className={`absolute inset-0 bg-gradient-to-t ${effect.color} opacity-10`}
        style={{
          animation: 'flash 0.3s ease-out'
        }}
      />

      <style>{`
        @keyframes gesturePop {
          0% {
            transform: scale(0);
            opacity: 0;
          }
          50% {
            transform: scale(1.2);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        @keyframes textSlideUp {
          0% {
            transform: translateX(-50%) translateY(20px);
            opacity: 0;
          }
          100% {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
          }
        }

        @keyframes particle {
          0% {
            transform: translate(0, 0) scale(1);
            opacity: 1;
          }
          100% {
            transform: translate(var(--tx), var(--ty)) scale(0);
            opacity: 0;
          }
        }

        @keyframes flash {
          0% {
            opacity: 0.3;
          }
          100% {
            opacity: 0;
          }
        }

        @keyframes ripple {
          0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 0.8;
          }
          100% {
            transform: translate(-50%, -50%) scale(3);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

const GestureToast = ({ gesture, onClose }) => {
  useEffect(() => {
    if (!gesture) return;
    
    const timer = setTimeout(() => {
      onClose?.();
    }, 2000);

    return () => clearTimeout(timer);
  }, [gesture, onClose]);

  if (!gesture) return null;

  const effect = gestureEffects[gesture.type] || gestureEffects.open_palm;

  return (
    <div className="fixed top-20 left-1/2 -translate-x-1/2 z-40">
      <div 
        className={`flex items-center gap-3 ${effect.bgColor} backdrop-blur-md border ${effect.borderColor} rounded-2xl px-6 py-3 shadow-2xl`}
        style={{
          animation: 'slideDown 0.3s ease-out'
        }}
      >
        <span className="text-3xl">{effect.icon}</span>
        <div>
          <div className="text-white font-semibold">{effect.text}</div>
          <div className="text-xs text-slate-300">手势识别</div>
        </div>
        <div className="text-xs text-slate-400">
          {Math.round(gesture.confidence * 100)}%
        </div>
      </div>
      <style>{`
        @keyframes slideDown {
          0% {
            transform: translateX(-50%) translateY(-20px);
            opacity: 0;
          }
          100% {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

export { GestureEffect, GestureToast };
export default GestureEffect;

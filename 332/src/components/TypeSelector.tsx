import { motion } from 'framer-motion';
import { Type, Link, User, Wifi, Mail } from 'lucide-react';
import type { QRCodeType } from '@/types';
import { cn } from '@/lib/utils';

interface TypeSelectorProps {
  value: QRCodeType;
  onChange: (type: QRCodeType) => void;
}

const types: Array<{ value: QRCodeType; label: string; icon: React.ElementType }> = [
  { value: 'text', label: '文本', icon: Type },
  { value: 'url', label: '网址', icon: Link },
  { value: 'vcard', label: '名片', icon: User },
  { value: 'wifi', label: 'WiFi', icon: Wifi },
  { value: 'email', label: '邮件', icon: Mail },
];

export default function TypeSelector({ value, onChange }: TypeSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {types.map(({ value: typeValue, label, icon: Icon }) => (
        <motion.button
          key={typeValue}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onChange(typeValue)}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all duration-200 border',
            value === typeValue
              ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white border-transparent shadow-lg shadow-blue-500/30'
              : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-500 hover:text-white'
          )}
        >
          <Icon size={16} />
          {label}
        </motion.button>
      ))}
    </div>
  );
}

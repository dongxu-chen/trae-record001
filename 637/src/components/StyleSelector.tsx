import type { NamingStyle } from '../../shared/types';
import { cn } from '../lib/utils';

interface StyleSelectorProps {
  value: NamingStyle;
  onChange: (style: NamingStyle) => void;
}

const styles: { value: NamingStyle; label: string; example: string }[] = [
  { value: 'camelCase', label: 'camelCase', example: 'userName' },
  { value: 'snake_case', label: 'snake_case', example: 'user_name' },
  { value: 'PascalCase', label: 'PascalCase', example: 'UserName' },
  { value: 'kebab-case', label: 'kebab-case', example: 'user-name' },
  { value: 'SCREAMING_SNAKE_CASE', label: 'UPPER_SNAKE', example: 'USER_NAME' }
];

const StyleSelector = ({ value, onChange }: StyleSelectorProps) => {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700">命名风格</label>
      <div className="flex flex-wrap gap-2">
        {styles.map((style) => (
          <button
            key={style.value}
            onClick={() => onChange(style.value)}
            className={cn(
              'px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 border',
              value === style.value
                ? 'bg-blue-500 text-white border-blue-500 shadow-md shadow-blue-500/30'
                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300 hover:text-blue-600'
            )}
          >
            <div className="font-mono text-xs">{style.example}</div>
            <div className="text-[10px] opacity-75">{style.label}</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default StyleSelector;

import type { CardTemplate } from '@/types';

interface TemplateCardProps {
  template: CardTemplate;
  selected: boolean;
  onClick: () => void;
}

const STYLE_BADGES: Record<string, string> = {
  fantasy: '奇幻',
  'sci-fi': '科幻',
  minimal: '极简',
  classic: '经典',
  custom: '自定义',
};

export default function TemplateCard({ template, selected, onClick }: TemplateCardProps) {
  return (
    <button
      onClick={onClick}
      className={`relative flex flex-col items-center p-3 rounded-lg border-2 transition-all duration-200 cursor-pointer min-w-[140px] ${
        selected
          ? 'border-gold-500 shadow-[0_0_15px_rgba(212,168,83,0.4)] bg-dark-700'
          : 'border-dark-600 bg-dark-800 hover:border-dark-600 hover:bg-dark-700 hover:shadow-[0_0_10px_rgba(212,168,83,0.15)]'
      }`}
    >
      <div
        className="w-[100px] h-[140px] rounded-md mb-2 relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${template.colors.primary}, ${template.colors.secondary}, ${template.colors.background})`,
          border: `${template.borders.width}px solid ${template.borders.color}`,
          borderRadius: `${template.borders.radius}px`,
        }}
      >
        <div
          className="absolute inset-2 border rounded-sm"
          style={{ borderColor: template.colors.accent + '60' }}
        />
        <div
          className="absolute bottom-1 left-1 right-1 text-center font-cinzel text-[8px] truncate"
          style={{ color: template.colors.text }}
        >
          {template.name}
        </div>
      </div>

      <span className="font-cinzel text-xs text-parchment-200 truncate w-full text-center">
        {template.name}
      </span>

      <span
        className="text-[10px] mt-1 px-1.5 py-0.5 rounded font-cinzel"
        style={{
          background: template.colors.primary + '30',
          color: template.colors.accent,
        }}
      >
        {STYLE_BADGES[template.style] || template.style}
      </span>

      {template.builtIn && (
        <span className="absolute top-1 right-1 text-[8px] bg-dark-600 text-gold-500 px-1 rounded font-cinzel">
          内置
        </span>
      )}
    </button>
  );
}

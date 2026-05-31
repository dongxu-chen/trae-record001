import { Users, Calendar, BookOpen, Quote, ChevronRight, Plus, Check } from 'lucide-react';
import type { Paper } from '@/types';
import { useAppStore } from '@/store';

interface PaperCardProps {
  paper: Paper;
  onSelect?: (paper: Paper) => void;
  showActions?: boolean;
}

export function PaperCard({ paper, onSelect, showActions = true }: PaperCardProps) {
  const { selectedPapers, addSelectedPaper, removeSelectedPaper } = useAppStore();
  const isSelected = selectedPapers.some((p) => p.doi === paper.doi);

  const handleToggleSelect = () => {
    if (isSelected) {
      removeSelectedPaper(paper.doi);
    } else {
      addSelectedPaper(paper);
    }
  };

  return (
    <div className="group glass rounded-xl p-5 hover:bg-dark-700/60 transition-all duration-300 hover:border-accent-blue/30 hover:shadow-xl hover:shadow-accent-blue/5 animate-fade-in">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center group-hover:scale-110 transition-transform">
          <BookOpen className="w-5 h-5 text-white" />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white group-hover:text-accent-blue transition-colors line-clamp-2 mb-2">
            {paper.title}
          </h3>

          <div className="flex flex-wrap items-center gap-3 text-sm text-dark-400 mb-3">
            <div className="flex items-center gap-1">
              <Users className="w-3.5 h-3.5" />
              <span className="truncate max-w-[200px]">
                {paper.authors.map((a) => a.name).join(', ')}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              <span>{paper.year}</span>
            </div>
            <div className="flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5" />
              <span className="truncate max-w-[150px]">{paper.venue}</span>
            </div>
          </div>

          {paper.abstract && (
            <p className="text-sm text-dark-400 line-clamp-2 mb-3">
              {paper.abstract}
            </p>
          )}

          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-1 text-xs rounded-full font-medium ${
                paper.source === 'crossref'
                  ? 'bg-accent-blue/20 text-accent-blue'
                  : 'bg-accent-green/20 text-accent-green'
              }`}
            >
              {paper.source.toUpperCase()}
            </span>

            <div className="flex items-center gap-1 px-3 py-1 bg-accent-amber/10 text-accent-amber rounded-full text-xs font-medium">
              <Quote className="w-3 h-3" />
              <span>{paper.citations.toLocaleString()} 引用</span>
            </div>

            {paper.keywords && paper.keywords.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {paper.keywords.slice(0, 3).map((kw, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs bg-dark-600/50 text-dark-300 rounded-md"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {showActions && (
          <div className="flex flex-col gap-2">
            <button
              onClick={handleToggleSelect}
              className={`p-2 rounded-lg transition-all ${
                isSelected
                  ? 'bg-accent-green text-white'
                  : 'bg-dark-700 text-dark-400 hover:bg-dark-600 hover:text-white'
              }`}
            >
              {isSelected ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            </button>

            {onSelect && (
              <button
                onClick={() => onSelect(paper)}
                className="p-2 rounded-lg bg-dark-700 text-dark-400 hover:bg-accent-blue hover:text-white transition-all group/btn"
              >
                <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-0.5 transition-transform" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

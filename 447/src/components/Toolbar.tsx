import { useState } from 'react';
import { symbolCategories } from '@/utils/symbols';
import { getMathQuillInstance } from '@/utils/mathquillInstance';

function isMatrixLatex(latex: string): boolean {
  return latex.startsWith('\\begin');
}

function insertSymbol(latex: string) {
  const mq = getMathQuillInstance();
  if (!mq) return;

  if (isMatrixLatex(latex)) {
    mq.write(latex);
  } else {
    const cmdLatex = latex.replace(/^\\/, '').replace(/\{\}/g, '');
    if (cmdLatex && latex.includes('\\')) {
      mq.cmd(cmdLatex);
    } else {
      mq.write(latex);
    }
  }
  mq.focus();
}

export default function Toolbar() {
  const [activeCategory, setActiveCategory] = useState('basic');

  const activeSymbols = symbolCategories.find((c) => c.id === activeCategory)?.symbols ?? [];

  return (
    <div className="bg-bg-secondary border-t border-border-custom px-3 py-2">
      <div className="flex gap-1 mb-2">
        {symbolCategories.map((category) => (
          <button
            key={category.id}
            onClick={() => setActiveCategory(category.id)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              activeCategory === category.id
                ? 'bg-accent text-bg-primary font-medium'
                : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
            }`}
          >
            {category.name}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1">
        {activeSymbols.map((symbol) => (
          <button
            key={symbol.latex}
            onClick={() => insertSymbol(symbol.latex)}
            title={symbol.label}
            className="px-2 py-1.5 text-sm bg-bg-tertiary text-text-primary rounded hover:bg-accent/20 transition-colors min-w-[36px] text-center"
          >
            {symbol.display}
          </button>
        ))}
      </div>
    </div>
  );
}

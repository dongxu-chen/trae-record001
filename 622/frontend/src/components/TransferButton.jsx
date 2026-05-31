import { Wand2, Loader2 } from 'lucide-react';

function TransferButton({ onClick, disabled, isProcessing }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isProcessing}
      className={`flex-1 px-6 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
        disabled || isProcessing
          ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
          : 'bg-gradient-to-r from-primary-500 to-accent-500 text-white hover:shadow-lg hover:shadow-primary-500/25 hover:-translate-y-0.5'
      }`}
    >
      {isProcessing ? (
        <>
          <Loader2 className="w-5 h-5 animate-spin" />
          处理中...
        </>
      ) : (
        <>
          <Wand2 className="w-5 h-5" />
          开始风格迁移
        </>
      )}
    </button>
  );
}

export default TransferButton;

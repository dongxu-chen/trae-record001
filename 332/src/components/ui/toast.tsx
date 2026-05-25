import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const icons: Record<ToastType, React.ElementType> = {
  success: CheckCircle,
  error: XCircle,
  info: AlertCircle,
  warning: AlertCircle,
};

const colors: Record<ToastType, string> = {
  success: 'bg-green-500/10 border-green-500/30 text-green-400',
  error: 'bg-red-500/10 border-red-500/30 text-red-400',
  info: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  warning: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon = icons[toast.type];
            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, x: 100 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 100 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-sm min-w-[280px] max-w-md',
                  colors[toast.type]
                )}
              >
                <Icon size={18} />
                <span className="flex-1 text-sm">{toast.message}</span>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="opacity-60 hover:opacity-100 transition-opacity"
                >
                  <X size={16} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

export const toast = {
  success: (message: string) => {
    const event = new CustomEvent('toast', {
      detail: { message, type: 'success' },
    });
    window.dispatchEvent(event);
  },
  error: (message: string) => {
    const event = new CustomEvent('toast', {
      detail: { message, type: 'error' },
    });
    window.dispatchEvent(event);
  },
  info: (message: string) => {
    const event = new CustomEvent('toast', {
      detail: { message, type: 'info' },
    });
    window.dispatchEvent(event);
  },
  warning: (message: string) => {
    const event = new CustomEvent('toast', {
      detail: { message, type: 'warning' },
    });
    window.dispatchEvent(event);
  },
};

export function GlobalToastListener() {
  const { showToast } = useToast();

  useEffect(() => {
    const handleToast = (e: Event) => {
      const customEvent = e as CustomEvent<{ message: string; type: ToastType }>;
      showToast(customEvent.detail.message, customEvent.detail.type);
    };

    window.addEventListener('toast', handleToast);
    return () => window.removeEventListener('toast', handleToast);
  }, [showToast]);

  return null;
}

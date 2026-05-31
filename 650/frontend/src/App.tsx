import { useEffect, Component, ReactNode } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AlertTriangle, RefreshCw } from "lucide-react";
import Home from "@/pages/Home";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAppStore } from "@/store/appStore";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error("Application Error:", error);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">发生错误</h2>
            <p className="text-slate-400 mb-4">
              应用程序遇到了意外问题。请尝试刷新页面。
            </p>
            {this.state.error && (
              <div className="bg-slate-800/50 rounded-lg p-3 mb-6 text-left">
                <p className="text-xs text-red-400 font-mono break-all">
                  {this.state.error.message}
                </p>
              </div>
            )}
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              重新加载
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function AppContent() {
  const { connect } = useWebSocket();
  const setConnection = useAppStore((state) => state.setConnection);

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/client-001";
    connect(wsUrl);
  }, [connect]);

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
          <AppContent />
        </div>
      </Router>
    </ErrorBoundary>
  );
}

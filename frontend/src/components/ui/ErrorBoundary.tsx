import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8 text-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h2 className="text-lg font-heading text-text">应用出现异常</h2>
          <p className="text-sm text-text-muted max-w-md">
            {this.state.error?.message || '未知错误'}
          </p>
          <div className="flex gap-3 mt-2">
            <button onClick={this.handleReset} className="btn-primary text-sm">
              重试
            </button>
            <button onClick={() => window.location.reload()} className="btn-ghost text-sm">
              刷新页面
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

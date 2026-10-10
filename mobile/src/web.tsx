import React from 'react';
import { createRoot } from 'react-dom/client';
import App from '../App';

const mount = document.getElementById('root');
if (!mount) throw new Error('Missing #root for the browser app');

class PreviewErrorBoundary extends React.Component<React.PropsWithChildren, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) return <pre style={{ margin: 18, padding: 14, whiteSpace: 'pre-wrap', color: '#8f1d1d', background: '#fff0f0', border: '1px solid #efbaba', borderRadius: 10, font: '13px/1.5 ui-monospace, monospace' }}>Browser preview error: {this.state.error.message}{'\n\n'}Open the dev console for the component stack.</pre>;
    return this.props.children;
  }
}

createRoot(mount).render(<PreviewErrorBoundary><App /></PreviewErrorBoundary>);

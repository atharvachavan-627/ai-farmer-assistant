import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './i18n';
import { AuthProvider } from './auth/AuthProvider';
import App from './App';
import './index.css';

// Opt-in, dev-only: `npm run dev:preview` swaps the HTTP layer for an in-browser stub.
const PREVIEW = import.meta.env.DEV && import.meta.env.VITE_UI_PREVIEW === 'true';

async function boot() {
  let Banner = null;
  if (PREVIEW) {
    await import('./dev/previewAdapter');
    Banner = (await import('./dev/PreviewBanner')).default;
  }
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <App />
          {Banner ? <Banner /> : null}
        </AuthProvider>
      </BrowserRouter>
    </StrictMode>,
  );
}

boot();

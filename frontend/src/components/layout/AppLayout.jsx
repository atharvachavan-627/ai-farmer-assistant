import { Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Header from './Header';

export default function AppLayout() {
  const { t } = useTranslation();
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        {t('nav.skip')}
      </a>
      <Header />
      <main id="main" className="app-main" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="footer">
        <div className="container footer__inner">
          <span>{t('app.name')}</span>
          <span>{t('app.tagline')}</span>
        </div>
      </footer>
    </div>
  );
}

import { Leaf, ScanLine, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Logo from '../common/Logo';
import LanguageSelector from '../layout/LanguageSelector';
import PageTransition from '../common/PageTransition';

/** Two-column layout shared by Login and Register. */
export default function AuthShell({ children, sideText }) {
  const { t } = useTranslation();
  return (
    <div className="auth">
      <aside className="auth__side" aria-hidden="false">
        <Logo light />
        <div className="auth__side-body">
          <span className="auth__badge" aria-hidden="true">
            <Leaf size={28} />
          </span>
          <h2>{t('home.hero.title')}</h2>
          <p>{sideText}</p>
          <ul className="auth__points">
            <li>
              <ScanLine size={18} aria-hidden="true" />
              {t('home.features.detection.title')}
            </li>
            <li>
              <ShieldCheck size={18} aria-hidden="true" />
              {t('home.features.treatment.title')}
            </li>
          </ul>
        </div>
      </aside>
      <main className="auth__main" id="main">
        <div className="auth__lang">
          <LanguageSelector />
        </div>
        <PageTransition className="auth__card">{children}</PageTransition>
      </main>
    </div>
  );
}

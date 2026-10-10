import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { History, Home, Library, Menu, ScanLine, X } from 'lucide-react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Logo from '../common/Logo';
import LanguageSelector from './LanguageSelector';
import UserMenu from './UserMenu';

const NAV = [
  { to: '/', key: 'nav.home', icon: Home, end: true },
  { to: '/analyse', key: 'nav.analyse', icon: ScanLine },
  { to: '/history', key: 'nav.history', icon: History },
  { to: '/info', key: 'nav.guide', icon: Library },
];

export default function Header() {
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const reduce = useReducedMotion();

  useEffect(() => setMobileOpen(false), [location.pathname]);

  const linkClass = ({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`;

  return (
    <header className="header">
      <div className="header__inner container">
        <Link to="/" className="header__brand" aria-label={t('app.name')}>
          <Logo />
        </Link>

        <nav className="header__nav" aria-label={t('nav.main')}>
          {NAV.map(({ to, key, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              {t(key)}
            </NavLink>
          ))}
        </nav>

        <div className="header__actions">
          <LanguageSelector />
          <UserMenu />
          <button
            type="button"
            className="icon-btn header__burger"
            aria-label={t('nav.menu')}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            onClick={() => setMobileOpen((o) => !o)}
          >
            {mobileOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen ? (
          <motion.nav
            id="mobile-nav"
            className="mobile-nav"
            aria-label={t('nav.main')}
            initial={reduce ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: reduce ? 0 : 0.2 }}
          >
            <div className="container mobile-nav__inner">
              {NAV.map(({ to, key, end, icon: Icon }) => (
                <NavLink key={to} to={to} end={end} className={linkClass}>
                  <Icon size={18} aria-hidden="true" />
                  {t(key)}
                </NavLink>
              ))}
            </div>
          </motion.nav>
        ) : null}
      </AnimatePresence>
    </header>
  );
}

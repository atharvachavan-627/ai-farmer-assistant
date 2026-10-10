import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/useAuth';
import { useDropdown } from '../../hooks/useDropdown';

const initials = (user) => {
  const source = (user?.name || user?.email || '?').trim();
  const parts = source.split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : source.slice(0, 2);
  return letters.toUpperCase();
};

export default function UserMenu() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { open, toggle, ref } = useDropdown();
  const reduce = useReducedMotion();

  const onLogout = async () => {
    try {
      await logout();
    } finally {
      navigate('/login', { replace: true });
    }
  };

  return (
    <div className="dropdown" ref={ref}>
      <button
        type="button"
        className="avatar"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('nav.profile')}
        onClick={toggle}
      >
        {initials(user)}
      </button>
      <AnimatePresence>
        {open ? (
          <motion.div
            className="dropdown__menu dropdown__menu--wide"
            role="menu"
            initial={reduce ? false : { opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: -6 }}
            transition={{ duration: reduce ? 0 : 0.14 }}
          >
            <div className="dropdown__profile">
              {user?.name ? <strong>{user.name}</strong> : null}
              {user?.email ? <span>{user.email}</span> : null}
            </div>
            <button type="button" role="menuitem" className="dropdown__item" onClick={onLogout}>
              <span>{t('nav.logout')}</span>
              <LogOut size={16} aria-hidden="true" />
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

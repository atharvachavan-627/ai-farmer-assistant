import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Check, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGUAGES, setLanguage } from '../../i18n';
import { useDropdown } from '../../hooks/useDropdown';

export default function LanguageSelector() {
  const { t, i18n } = useTranslation();
  const { open, setOpen, toggle, ref } = useDropdown();
  const reduce = useReducedMotion();
  const current = SUPPORTED_LANGUAGES.find((l) => l.code === i18n.resolvedLanguage) || SUPPORTED_LANGUAGES[0];

  return (
    <div className="dropdown" ref={ref}>
      <button
        type="button"
        className="icon-btn icon-btn--label"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`${t('nav.language')}: ${current.label}`}
        onClick={toggle}
      >
        <Globe size={18} aria-hidden="true" />
        <span>{current.short}</span>
      </button>
      <AnimatePresence>
        {open ? (
          <motion.ul
            className="dropdown__menu"
            role="menu"
            aria-label={t('nav.language')}
            initial={reduce ? false : { opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: -6 }}
            transition={{ duration: reduce ? 0 : 0.14 }}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <li key={lang.code} role="none">
                <button
                  type="button"
                  role="menuitemradio"
                  aria-checked={lang.code === current.code}
                  className="dropdown__item"
                  lang={lang.code}
                  onClick={() => {
                    setLanguage(lang.code);
                    setOpen(false);
                  }}
                >
                  <span>{lang.label}</span>
                  {lang.code === current.code ? <Check size={16} aria-hidden="true" /> : null}
                </button>
              </li>
            ))}
          </motion.ul>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

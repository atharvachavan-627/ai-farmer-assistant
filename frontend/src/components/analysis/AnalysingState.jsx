import { motion, useReducedMotion } from 'framer-motion';
import { ScanSearch } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** Indeterminate loading state - deliberately shows no percentage because none is known. */
export default function AnalysingState({ previewUrl }) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  return (
    <div className="analysing card" role="status" aria-live="polite">
      {previewUrl ? (
        <div className="analysing__frame">
          <img src={previewUrl} alt="" />
          {reduce ? null : (
            <motion.span
              className="analysing__scan"
              aria-hidden="true"
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </div>
      ) : null}
      <div className="analysing__text">
        <ScanSearch size={22} aria-hidden="true" />
        <div>
          <p className="analysing__title">{t('analyse.analysing')}</p>
          <p className="note">{t('analyse.analysingNote')}</p>
        </div>
      </div>
    </div>
  );
}

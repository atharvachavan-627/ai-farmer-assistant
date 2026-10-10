import { motion, useReducedMotion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { formatPercent, LOW_CONFIDENCE_THRESHOLD } from '../../utils/format';

export default function ConfidenceBar({ value }) {
  const { t, i18n } = useTranslation();
  const reduce = useReducedMotion();
  if (typeof value !== 'number') return null;
  const clamped = Math.max(0, Math.min(1, value));
  const low = clamped < LOW_CONFIDENCE_THRESHOLD;
  return (
    <div className="confidence">
      <div className="confidence__head">
        <span>{t('analyse.result.confidence')}</span>
        <strong>{formatPercent(clamped, i18n.resolvedLanguage)}</strong>
      </div>
      <div
        className="confidence__track"
        role="meter"
        aria-label={t('analyse.result.confidence')}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped * 100)}
      >
        <motion.div
          className={`confidence__fill ${low ? 'confidence__fill--low' : ''}`}
          initial={reduce ? false : { width: 0 }}
          animate={{ width: `${clamped * 100}%` }}
          transition={{ duration: reduce ? 0 : 0.7, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

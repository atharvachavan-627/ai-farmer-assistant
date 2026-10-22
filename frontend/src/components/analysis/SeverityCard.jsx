import { motion, useReducedMotion } from 'framer-motion';
import { Activity, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function SeverityCard({ severity }) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();

  // If severity data is not present in response, do not render
  if (!severity || typeof severity !== 'object') {
    return null;
  }

  const {
    status,
    estimatedAffectedAreaPercent,
    category,
    message,
    disclaimer,
  } = severity;

  const hasPercent =
    typeof estimatedAffectedAreaPercent === 'number' &&
    Number.isFinite(estimatedAffectedAreaPercent) &&
    !Number.isNaN(estimatedAffectedAreaPercent);

  const clampedPercent = hasPercent
    ? Math.max(0, Math.min(100, Math.round(estimatedAffectedAreaPercent * 10) / 10))
    : null;

  const isHealthy = status === 'healthy_leaf' || (hasPercent && clampedPercent === 0);
  const isEstimated = status === 'estimated' || isHealthy;

  // Category display label with fallback
  const categoryLabel = category
    ? t(`analyse.result.severity.categories.${category}`, category.charAt(0).toUpperCase() + category.slice(1))
    : t('analyse.result.severity.categories.unavailable', 'Unavailable');

  // Status display label with fallback
  const statusLabel = status
    ? t(`analyse.result.severity.statuses.${status}`, status.replace(/_/g, ' '))
    : '';

  return (
    <motion.section
      className="card severity-card"
      aria-labelledby="severity-card-title"
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.3, ease: 'easeOut' }}
    >
      <div className="severity-card__header">
        <div className="severity-card__title-wrap">
          <Activity size={18} aria-hidden="true" className="severity-card__icon" />
          <h3 id="severity-card-title" className="severity-card__title">
            {t('analyse.result.severity.title', 'Disease Severity')}
          </h3>
        </div>
        <div className="severity-card__badges">
          {category ? (
            <span className={`tag severity-tag severity-tag--${category}`}>
              {categoryLabel}
            </span>
          ) : null}
          {statusLabel ? (
            <span className="tag tag--outline">
              {statusLabel}
            </span>
          ) : null}
        </div>
      </div>

      {hasPercent ? (
        <div className="severity-card__body">
          <div className="severity-card__metric">
            <span className="severity-card__label">
              {t('analyse.result.severity.affectedArea', 'Estimated Affected Leaf Area')}
            </span>
            <strong className="severity-card__value">
              {clampedPercent.toFixed(1)}%
            </strong>
          </div>

          <div
            className="severity-card__track"
            role="meter"
            aria-label={t('analyse.result.severity.affectedArea', 'Estimated Affected Leaf Area')}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={clampedPercent}
            aria-valuetext={`${clampedPercent.toFixed(1)} percent affected, category ${categoryLabel}`}
          >
            <motion.div
              className={`severity-card__fill severity-card__fill--${category || 'default'}`}
              initial={reduce ? false : { width: 0 }}
              animate={{ width: `${clampedPercent}%` }}
              transition={{ duration: reduce ? 0 : 0.6, ease: 'easeOut' }}
            />
          </div>

          <div className="severity-card__meta">
            <span>
              <strong>{t('analyse.result.severity.categoryTitle', 'Severity Category')}:</strong> {categoryLabel}
            </span>
            {message && !isHealthy ? (
              <span className="severity-card__msg">{message}</span>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="severity-card__notice" role="status">
          <Info size={16} aria-hidden="true" />
          <p>
            {message ||
              t(
                'analyse.result.severity.unavailableNotice',
                'Severity estimation is unavailable or unreliable for this image.'
              )}
          </p>
        </div>
      )}

      {isHealthy ? (
        <div className="severity-card__healthy-note">
          <CheckCircle2 size={16} aria-hidden="true" />
          <p>
            {t(
              'analyse.result.severity.healthyBody',
              'No active foliar lesions were detected within the visible leaf surface.'
            )}
          </p>
        </div>
      ) : null}

      <p className="note severity-card__disclaimer">
        {disclaimer ||
          t(
            'analyse.result.severity.note',
            'Note: This estimate describes visible affected leaf area in the submitted image. It does not establish the percentage of the entire plant affected or predict future disease progression.'
          )}
      </p>
    </motion.section>
  );
}

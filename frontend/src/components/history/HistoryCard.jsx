import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Calendar, ImageOff, Sprout, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resolveMediaUrl } from '../../services/apiClient';
import { cropLabel, formatDateTime, formatPercent } from '../../utils/format';

export default function HistoryCard({ record, onDelete }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage;
  const reduce = useReducedMotion();
  const image = resolveMediaUrl(record.imageUrl);
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <motion.article
      className="card card--hover record"
      layout={!reduce}
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduce ? undefined : { opacity: 0, scale: 0.95 }}
      transition={{ duration: reduce ? 0 : 0.22 }}
    >
      <div className="record__media">
        {image && !imgFailed ? (
          <img
            src={image}
            alt={t('history.imageAlt', { disease: record.disease })}
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <span className="record__placeholder" aria-hidden="true">
            <ImageOff size={28} />
          </span>
        )}
      </div>
      <div className="record__body">
        <h3 className="record__title">{record.disease}</h3>
        <p className="record__line">
          <Sprout size={14} aria-hidden="true" /> {cropLabel(record.crop, t)}
        </p>
        <p className="record__line">
          <Calendar size={14} aria-hidden="true" /> {formatDateTime(record.createdAt, lang)}
        </p>
        {record.confidence != null ? (
          <p className="chip">
            {t('analyse.result.confidence')}: {formatPercent(record.confidence, lang)}
          </p>
        ) : null}
      </div>
      <div className="record__footer">
        {record.diseaseCode ? (
          <Link
            to={`/info/${encodeURIComponent(record.diseaseCode)}`}
            className="btn btn--secondary btn--sm record__cta"
            aria-label={`${t('common.viewDetails')}: ${record.disease}`}
          >
            {t('common.viewDetails')}
          </Link>
        ) : <span />}
        {onDelete ? (
          <button
            type="button"
            className="btn btn--ghost btn--danger btn--sm record__delete"
            onClick={() => onDelete(record)}
            aria-label={`${t('history.delete') || 'Delete'}: ${record.disease}`}
            title={t('common.delete') || 'Delete record'}
          >
            <Trash2 size={16} aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </motion.article>
  );
}

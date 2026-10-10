import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, Leaf } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resolveMediaUrl } from '../../services/apiClient';
import { cropLabel } from '../../utils/format';

export default function DiseaseCard({ disease, compact = false }) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const image = resolveMediaUrl(disease.imageUrl);

  return (
    <motion.article
      className="card card--hover disease-card"
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.22 }}
    >
      <div className="disease-card__media">
        {image ? (
          <img src={image} alt={t('info.imageAlt', { disease: disease.name })} loading="lazy" />
        ) : (
          <span className="disease-card__placeholder" aria-hidden="true">
            <Leaf size={30} />
          </span>
        )}
      </div>
      <div className="disease-card__body">
        <div className="tags">
          {disease.crop ? <span className="tag">{cropLabel(disease.crop, t)}</span> : null}
          {disease.category ? <span className="tag tag--muted">{disease.category}</span> : null}
        </div>
        <h3 className="disease-card__title">{disease.name}</h3>
        {!compact && disease.symptomsSummary ? (
          <p className="disease-card__text">
            <strong>{t('info.symptoms')}: </strong>
            {disease.symptomsSummary}
          </p>
        ) : null}
        {!compact && disease.preventionSummary ? (
          <p className="disease-card__text">
            <strong>{t('info.prevention')}: </strong>
            {disease.preventionSummary}
          </p>
        ) : null}
        <Link
          to={`/info/${encodeURIComponent(disease.code)}`}
          className="link-arrow"
          aria-label={`${t('common.viewDetails')}: ${disease.name}`}
        >
          {t('common.viewDetails')}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
    </motion.article>
  );
}

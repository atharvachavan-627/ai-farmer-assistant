import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, Leaf } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resolveMediaUrl } from '../../services/apiClient';
import { cropLabel } from '../../utils/format';

const FALLBACK_IMAGE = '/images/diseases/leaf-fallback.jpg';

export default function DiseaseCard({ disease, compact = false }) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();

  const getInitialSrc = (url) => (url ? resolveMediaUrl(url) : resolveMediaUrl(FALLBACK_IMAGE));
  const [imgSrc, setImgSrc] = useState(() => getInitialSrc(disease.imageUrl));
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setImgSrc(getInitialSrc(disease.imageUrl));
    setHasError(false);
  }, [disease.imageUrl]);

  const handleImageError = () => {
    // If loading from full backend URL failed, retry relative path served by Vite/frontend
    if (imgSrc && /^https?:\/\//i.test(imgSrc)) {
      try {
        const pathname = new URL(imgSrc, window.location.href).pathname;
        if (pathname && imgSrc !== pathname) {
          setImgSrc(pathname);
          return;
        }
      } catch {
        /* ignore URL parse error */
      }
    }

    const fallback = resolveMediaUrl(FALLBACK_IMAGE);
    if (imgSrc !== fallback && imgSrc !== FALLBACK_IMAGE) {
      setImgSrc(fallback);
    } else {
      setHasError(true);
    }
  };

  return (
    <motion.article
      className="card card--hover disease-card"
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.22 }}
    >
      <div className="disease-card__media">
        {imgSrc && !hasError ? (
          <img
            src={imgSrc}
            alt={t('info.imageAlt', { disease: disease.name })}
            loading="lazy"
            onError={handleImageError}
          />
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

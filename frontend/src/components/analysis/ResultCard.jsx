import { motion, useReducedMotion } from 'framer-motion';
import { AlertTriangle, BookOpen, FlaskConical, History, Leaf, ScanLine, ShieldCheck, Sprout } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ConfidenceBar from './ConfidenceBar';
import BulletList from '../common/BulletList';
import SectionCard from '../common/SectionCard';
import { cropLabel, formatDateTime, LOW_CONFIDENCE_THRESHOLD } from '../../utils/format';

export default function ResultCard({ result, imageUrl, analysedAt, onReset }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage;
  const reduce = useReducedMotion();
  const low = result.lowConfidence || (typeof result.confidence === 'number' && result.confidence < LOW_CONFIDENCE_THRESHOLD);
  const { summary, preventive, organic, chemical } = result.treatment;
  const hasTreatment = summary || preventive.length || organic.length || chemical.length;

  return (
    <motion.section
      className="result"
      aria-labelledby="result-title"
      initial={reduce ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.35, ease: 'easeOut' }}
    >
      <div className="result__top card">
        {imageUrl ? (
          <figure className="result__figure">
            <img src={imageUrl} alt={t('analyse.result.imageAlt')} />
            <figcaption>{t('analyse.result.image')}</figcaption>
          </figure>
        ) : null}
        <div className="result__summary">
          <p className="eyebrow">{t('analyse.result.title')}</p>
          <h2 id="result-title" className="result__disease">
            {result.disease}
          </h2>
          <dl className="meta">
            <div>
              <dt>{t('analyse.result.crop')}</dt>
              <dd>
                <Sprout size={14} aria-hidden="true" /> {cropLabel(result.crop, t)}
              </dd>
            </div>
            <div>
              <dt>{t('analyse.result.analysedAt')}</dt>
              <dd>{formatDateTime(result.createdAt || analysedAt, lang)}</dd>
            </div>
            {result.modelVersion ? (
              <div>
                <dt>{t('analyse.result.model')}</dt>
                <dd>{result.modelVersion}</dd>
              </div>
            ) : null}
          </dl>
          <ConfidenceBar value={result.confidence} />
          <p className="note">{t('analyse.result.confidenceNote')}</p>
          {low ? (
            <div className="alert alert--warning" role="alert">
              <AlertTriangle size={18} aria-hidden="true" />
              <p>{t('analyse.result.lowConfidence')}</p>
            </div>
          ) : null}
          <div className="result__actions">
            {result.diseaseCode ? (
              <Link to={`/info/${encodeURIComponent(result.diseaseCode)}`} className="btn btn--primary">
                <BookOpen size={18} aria-hidden="true" />
                {t('analyse.result.details')}
              </Link>
            ) : null}
            <button type="button" className="btn btn--secondary" onClick={onReset}>
              <ScanLine size={18} aria-hidden="true" />
              {t('analyse.result.another')}
            </button>
            <Link to="/history" className="btn btn--ghost">
              <History size={18} aria-hidden="true" />
              {t('analyse.result.history')}
            </Link>
          </div>
        </div>
      </div>

      {hasTreatment ? (
        <div className="result__grid">
          {summary ? (
            <SectionCard icon={Leaf} title={t('analyse.result.summary')}>
              <p>{summary}</p>
            </SectionCard>
          ) : null}
          {preventive.length ? (
            <SectionCard icon={ShieldCheck} title={t('analyse.result.prevention')}>
              <BulletList items={preventive} />
            </SectionCard>
          ) : null}
          {organic.length ? (
            <SectionCard icon={Sprout} title={t('analyse.result.organic')}>
              <BulletList items={organic} />
            </SectionCard>
          ) : null}
          {chemical.length ? (
            <SectionCard icon={FlaskConical} title={t('analyse.result.chemical')} tone="caution">
              <BulletList items={chemical} />
              <p className="note">{t('analyse.result.chemicalNote')}</p>
            </SectionCard>
          ) : null}
        </div>
      ) : (
        <p className="note">{t('analyse.result.noTreatment')}</p>
      )}
    </motion.section>
  );
}

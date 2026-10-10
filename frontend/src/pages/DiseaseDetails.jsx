import { AlertTriangle, ArrowLeft, Eye, FlaskConical, Info, Leaf, ScanLine, Sprout, Stethoscope, Sun, ShieldCheck, Tractor } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PageTransition from '../components/common/PageTransition';
import ErrorState from '../components/common/ErrorState';
import BulletList from '../components/common/BulletList';
import SectionCard from '../components/common/SectionCard';
import { Skeleton } from '../components/common/Skeleton';
import { diseaseService } from '../services/diseaseService';
import { resolveMediaUrl } from '../services/apiClient';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { cropLabel } from '../utils/format';

export default function DiseaseDetails() {
  const { diseaseCode } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage;
  const { status, data, error, reload } = useFetch(
    (signal) => diseaseService.get(diseaseCode, lang, signal),
    [diseaseCode, lang],
  );
  useDocumentTitle(data?.name || t('nav.guide'));

  const back = (
    <Link to="/info" className="link-arrow link-arrow--back">
      <ArrowLeft size={16} aria-hidden="true" />
      {t('details.back')}
    </Link>
  );

  if (status === 'loading') {
    return (
      <div className="container page" role="status" aria-busy="true">
        <span className="visually-hidden">{t('common.loading')}</span>
        {back}
        <Skeleton height={36} width="50%" />
        <div style={{ height: 16 }} />
        <Skeleton height={220} radius={16} />
      </div>
    );
  }

  if (status === 'error') {
    const notFound = error?.status === 404;
    return (
      <PageTransition className="container page">
        {back}
        <ErrorState
          error={notFound ? { kind: 'client', message: t('details.notFound') } : error}
          title={notFound ? undefined : t('details.error')}
          onRetry={notFound ? undefined : reload}
        />
      </PageTransition>
    );
  }

  const d = data;
  const image = resolveMediaUrl(d.imageUrl);
  const showFallback = d.contentLanguage && d.contentLanguage !== lang;
  const showChemical = d.chemicalVerified && d.chemical.length > 0;

  const sections = [
    { key: 'symptoms', icon: Eye, items: d.symptoms },
    { key: 'conditions', icon: Sun, items: d.favourableConditions },
    { key: 'prevention', icon: ShieldCheck, items: d.preventive },
    { key: 'cultural', icon: Tractor, items: d.cultural },
    { key: 'organic', icon: Sprout, items: d.organic },
  ].filter((s) => s.items.length > 0);

  return (
    <PageTransition className="container page">
      {back}

      <header className="detail-head card">
        {image ? <img src={image} alt={t('info.imageAlt', { disease: d.name })} className="detail-head__img" /> : null}
        <div>
          <p className="eyebrow">
            {t('details.affects')}: {cropLabel(d.crop, t)}
          </p>
          <h1>{d.name}</h1>
          {d.category ? <span className="tag tag--muted">{d.category}</span> : null}
          {d.overview ? (
            <>
              <h2 className="detail-head__sub">{t('details.overview')}</h2>
              <p>{d.overview}</p>
            </>
          ) : null}
          <Link to="/analyse" className="btn btn--primary detail-head__cta">
            <ScanLine size={18} aria-hidden="true" />
            {t('details.analyse')}
          </Link>
        </div>
      </header>

      {showFallback ? (
        <div className="alert alert--info" role="note">
          <Info size={18} aria-hidden="true" />
          <p>{t('common.fallbackNotice')}</p>
        </div>
      ) : null}

      <div className="result__grid">
        {sections.map(({ key, icon, items }) => (
          <SectionCard key={key} icon={icon} title={t(`details.${key}`)}>
            <BulletList items={items} />
          </SectionCard>
        ))}

        <SectionCard icon={FlaskConical} title={t('details.chemical')} tone="caution">
          {showChemical ? (
            <>
              <BulletList items={d.chemical} />
              <p className="note">{t('details.chemicalNote')}</p>
            </>
          ) : (
            <p className="note">{t('details.chemicalUnverified')}</p>
          )}
        </SectionCard>

        <SectionCard icon={Stethoscope} title={t('details.expert')} tone="expert">
          {d.consultExpert.length ? <BulletList items={d.consultExpert} /> : <p className="note">{t('details.none')}</p>}
        </SectionCard>
      </div>

      {sections.length === 0 && !d.overview ? (
        <p className="note">
          <Leaf size={14} aria-hidden="true" /> <AlertTriangle size={14} aria-hidden="true" /> {t('details.none')}
        </p>
      ) : null}
    </PageTransition>
  );
}

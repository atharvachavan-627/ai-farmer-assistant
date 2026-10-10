import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, BookOpen, History, Library, ScanLine, ShieldCheck, Sprout } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/useAuth';
import PageTransition from '../components/common/PageTransition';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import { SkeletonGrid } from '../components/common/Skeleton';
import DiseaseCard from '../components/disease/DiseaseCard';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { diseaseService } from '../services/diseaseService';

const FEATURES = [
  { key: 'detection', icon: ScanLine },
  { key: 'history', icon: History },
  { key: 'info', icon: BookOpen },
  { key: 'treatment', icon: ShieldCheck },
];
const STEPS = ['s1', 's2', 's3', 's4'];
const RECENT_COUNT = 3;

/** Newest first when the backend supplies created_at on every entry; otherwise keep backend order. */
const pickRecent = (items) => {
  const dated = items.every((d) => d.createdAt && !Number.isNaN(new Date(d.createdAt).getTime()));
  const sorted = dated ? [...items].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)) : items;
  return sorted.slice(0, RECENT_COUNT);
};

export default function Home() {
  const { t, i18n } = useTranslation();
  useDocumentTitle(t('nav.home'));
  const { user } = useAuth();
  const reduce = useReducedMotion();
  const lang = i18n.resolvedLanguage;
  const recent = useFetch((signal) => diseaseService.list(lang, signal), [lang]);

  const firstName = user?.name?.trim().split(/\s+/)[0];

  return (
    <PageTransition>
      <section className="hero">
        <div className="container hero__inner">
          <div className="hero__copy">
            {firstName ? <p className="eyebrow">{t('home.hero.greeting', { name: firstName })}</p> : null}
            <h1 className="hero__title">{t('home.hero.title')}</h1>
            <p className="hero__text">{t('home.hero.subtitle')}</p>
            <div className="hero__actions">
              <Link to="/analyse" className="btn btn--primary btn--lg">
                <ScanLine size={20} aria-hidden="true" />
                {t('home.hero.cta1')}
              </Link>
              <Link to="/info" className="btn btn--light btn--lg">
                <Library size={20} aria-hidden="true" />
                {t('home.hero.cta2')}
              </Link>
            </div>
          </div>
          <div className="hero__art" aria-hidden="true">
            <motion.div
              className="hero__orb"
              animate={reduce ? undefined : { y: [0, -8, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Sprout size={96} strokeWidth={1.25} />
            </motion.div>
          </div>
        </div>
      </section>

      <section className="section container" aria-labelledby="features-title">
        <h2 id="features-title" className="section__title">
          {t('home.features.title')}
        </h2>
        <div className="grid grid--4">
          {FEATURES.map(({ key, icon: Icon }, i) => (
            <motion.article
              key={key}
              className="card card--hover feature"
              initial={reduce ? false : { opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: reduce ? 0 : 0.3, delay: reduce ? 0 : i * 0.05 }}
            >
              <span className="feature__icon" aria-hidden="true">
                <Icon size={22} />
              </span>
              <h3>{t(`home.features.${key}.title`)}</h3>
              <p>{t(`home.features.${key}.body`)}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section className="section section--tint" aria-labelledby="how-title">
        <div className="container">
          <h2 id="how-title" className="section__title">
            {t('home.how.title')}
          </h2>
          <ol className="steps">
            {STEPS.map((s, i) => (
              <li key={s} className="step">
                <span className="step__num" aria-hidden="true">
                  {i + 1}
                </span>
                <h3>{t(`home.how.${s}.title`)}</h3>
                <p>{t(`home.how.${s}.body`)}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section container" aria-labelledby="recent-title">
        <div className="section__head">
          <div>
            <h2 id="recent-title" className="section__title">
              {t('home.recent.title')}
            </h2>
            <p className="section__sub">{t('home.recent.subtitle')}</p>
          </div>
          <Link to="/info" className="link-arrow">
            {t('home.hero.cta2')}
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>

        {recent.status === 'loading' ? <SkeletonGrid count={RECENT_COUNT} label={t('common.loading')} /> : null}
        {recent.status === 'error' ? <ErrorState error={recent.error} onRetry={recent.reload} compact /> : null}
        {recent.status === 'success' && recent.data.length === 0 ? (
          <EmptyState icon={Library} title={t('home.recent.empty')} body={t('home.recent.emptyBody')} />
        ) : null}
        {recent.status === 'success' && recent.data.length > 0 ? (
          <div className="grid grid--cards">
            {pickRecent(recent.data).map((d) => (
              <DiseaseCard key={d.code} disease={d} compact />
            ))}
          </div>
        ) : null}
      </section>

      <section className="container section">
        <div className="cta">
          <div>
            <h2>{t('home.final.title')}</h2>
            <p>{t('home.final.body')}</p>
          </div>
          <Link to="/analyse" className="btn btn--light btn--lg">
            {t('home.final.cta')}
            <ArrowRight size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>
    </PageTransition>
  );
}

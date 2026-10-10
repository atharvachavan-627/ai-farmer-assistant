import { useMemo, useState } from 'react';
import { Library, Search, SearchX } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import PageTransition from '../components/common/PageTransition';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import { SkeletonGrid } from '../components/common/Skeleton';
import DiseaseCard from '../components/disease/DiseaseCard';
import { diseaseService } from '../services/diseaseService';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { cropLabel } from '../utils/format';

const unique = (values) => [...new Set(values.filter(Boolean))];

export default function DiseaseInfo() {
  const { t, i18n } = useTranslation();
  useDocumentTitle(t('nav.guide'));
  const lang = i18n.resolvedLanguage;
  const { status, data, error, reload } = useFetch((signal) => diseaseService.list(lang, signal), [lang]);

  const [search, setSearch] = useState('');
  const [crop, setCrop] = useState('');
  const [category, setCategory] = useState('');

  const crops = useMemo(() => unique((data || []).map((d) => d.crop)), [data]);
  const categories = useMemo(() => unique((data || []).map((d) => d.category)), [data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data || []).filter(
      (d) =>
        (!q || d.name?.toLowerCase().includes(q)) &&
        (!crop || d.crop === crop) &&
        (!category || d.category === category),
    );
  }, [data, search, crop, category]);

  const clear = () => {
    setSearch('');
    setCrop('');
    setCategory('');
  };

  return (
    <PageTransition className="container page">
      <header className="page__head">
        <h1>{t('info.title')}</h1>
        <p>{t('info.subtitle')}</p>
      </header>

      {status === 'loading' ? <SkeletonGrid count={6} label={t('common.loading')} /> : null}
      {status === 'error' ? <ErrorState error={error} title={t('info.error')} onRetry={reload} /> : null}

      {status === 'success' && data.length === 0 ? (
        <EmptyState icon={Library} title={t('info.empty.title')} body={t('info.empty.body')} />
      ) : null}

      {status === 'success' && data.length > 0 ? (
        <>
          <form className="filters card filters--info" onSubmit={(e) => e.preventDefault()} role="search" aria-label={t('info.title')}>
            <div className="filters__search">
              <label htmlFor="d-search" className="field__label">
                {t('info.search')}
              </label>
              <div className="field__control">
                <Search size={16} className="field__icon" aria-hidden="true" />
                <input
                  id="d-search"
                  type="search"
                  className="field__input field__input--icon"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label htmlFor="d-crop" className="field__label">
                {t('info.crop')}
              </label>
              <select id="d-crop" className="field__input" value={crop} onChange={(e) => setCrop(e.target.value)}>
                <option value="">{t('common.all')}</option>
                {crops.map((c) => (
                  <option key={c} value={c}>
                    {cropLabel(c, t)}
                  </option>
                ))}
              </select>
            </div>
            {categories.length > 0 ? (
              <div>
                <label htmlFor="d-cat" className="field__label">
                  {t('info.category')}
                </label>
                <select id="d-cat" className="field__input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="">{t('common.all')}</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
          </form>

          <p className="results-count" aria-live="polite">
            {t('info.count', { count: filtered.length })}
          </p>

          {filtered.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title={t('info.noMatch.title')}
              body={t('info.noMatch.body')}
              action={
                <button type="button" className="btn btn--secondary" onClick={clear}>
                  {t('common.clear')}
                </button>
              }
            />
          ) : (
            <div className="grid grid--cards">
              {filtered.map((d) => (
                <DiseaseCard key={d.code} disease={d} />
              ))}
            </div>
          )}
        </>
      ) : null}
    </PageTransition>
  );
}

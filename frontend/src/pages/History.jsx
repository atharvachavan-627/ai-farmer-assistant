import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Activity, ClipboardList, Search, SearchX, TrendingUp, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PageTransition from '../components/common/PageTransition';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import Spinner from '../components/common/Spinner';
import { SkeletonGrid } from '../components/common/Skeleton';
import HistoryCard from '../components/history/HistoryCard';
import { historyService } from '../services/historyService';
import { useDebounce } from '../hooks/useDebounce';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { HISTORY_PAGE_SIZE } from '../utils/constants';
import { cropLabel, formatDateTime } from '../utils/format';

const CROPS = ['tomato', 'potato'];
const INITIAL_FILTERS = { search: '', crop: '', dateFrom: '', dateTo: '', sort: 'newest' };

export default function History() {
  const { t, i18n } = useTranslation();
  useDocumentTitle(t('nav.history'));
  const lang = i18n.resolvedLanguage;

  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const debouncedSearch = useDebounce(filters.search);
  const [list, setList] = useState({ status: 'loading', items: [], total: 0, page: 1, error: null, loadingMore: false });
  const [reloadKey, setReloadKey] = useState(0);
  const requestId = useRef(0);

  const query = useMemo(
    () => ({
      search: debouncedSearch.trim(),
      crop: filters.crop,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      sort: filters.sort,
      page_size: HISTORY_PAGE_SIZE,
    }),
    [debouncedSearch, filters.crop, filters.dateFrom, filters.dateTo, filters.sort],
  );

  // Unfiltered overview for the stat tiles (total, latest, frequency summary).
  const overview = useFetch((signal) => historyService.list({ page: 1, page_size: 1, sort: 'newest' }, signal), [reloadKey]);

  // First page whenever the filters change.
  useEffect(() => {
    const controller = new AbortController();
    const id = ++requestId.current;
    setList((l) => ({ ...l, status: 'loading', error: null, page: 1 }));
    historyService
      .list({ ...query, page: 1 }, controller.signal)
      .then((res) => {
        if (id !== requestId.current) return;
        setList({ status: 'success', items: res.items, total: res.total, page: 1, error: null, loadingMore: false });
      })
      .catch((error) => {
        if (error?.code === 'ERR_CANCELED' || id !== requestId.current) return;
        setList({ status: 'error', items: [], total: 0, page: 1, error, loadingMore: false });
      });
    return () => controller.abort();
  }, [query, reloadKey]);

  const loadMore = useCallback(async () => {
    const nextPage = list.page + 1;
    setList((l) => ({ ...l, loadingMore: true }));
    try {
      const res = await historyService.list({ ...query, page: nextPage });
      setList((l) => ({ ...l, items: [...l.items, ...res.items], total: res.total, page: nextPage, loadingMore: false }));
    } catch (error) {
      setList((l) => ({ ...l, loadingMore: false, error }));
    }
  }, [list.page, query]);

  const setFilter = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));
  const filtersActive =
    filters.search || filters.crop || filters.dateFrom || filters.dateTo || filters.sort !== INITIAL_FILTERS.sort;
  const retryAll = () => setReloadKey((k) => k + 1);

  const totalAll = overview.data?.total;
  const latest = overview.data?.items?.[0];
  const frequency = useMemo(() => {
    if (overview.data?.byDisease?.length) return overview.data.byDisease;
    // Fallback: derive from the records loaded on screen when the backend sends no summary.
    const counts = new Map();
    list.items.forEach((r) => {
      if (!r.diseaseCode) return;
      const entry = counts.get(r.diseaseCode) || { diseaseCode: r.diseaseCode, disease: r.disease, count: 0 };
      entry.count += 1;
      counts.set(r.diseaseCode, entry);
    });
    return [...counts.values()];
  }, [overview.data, list.items]);
  const topFrequency = [...frequency].sort((a, b) => b.count - a.count).slice(0, 5);
  const maxCount = topFrequency[0]?.count || 1;

  const hasMore = list.items.length < list.total;
  const noRecordsAtAll = list.status === 'success' && list.total === 0 && !filtersActive;

  return (
    <PageTransition className="container page">
      <header className="page__head">
        <h1>{t('history.title')}</h1>
        <p>{t('history.subtitle')}</p>
      </header>

      {overview.status === 'success' && totalAll > 0 ? (
        <div className="stats">
          <div className="card stat">
            <Activity size={20} aria-hidden="true" />
            <p className="stat__label">{t('history.total')}</p>
            <p className="stat__value">{new Intl.NumberFormat(lang).format(totalAll)}</p>
          </div>
          {latest ? (
            <div className="card stat">
              <ClipboardList size={20} aria-hidden="true" />
              <p className="stat__label">{t('history.recent')}</p>
              <p className="stat__value stat__value--text">{latest.disease}</p>
              <p className="stat__sub">{formatDateTime(latest.createdAt, lang)}</p>
            </div>
          ) : null}
          {topFrequency.length ? (
            <div className="card stat stat--wide">
              <TrendingUp size={20} aria-hidden="true" />
              <p className="stat__label">{t('history.frequency')}</p>
              <ul className="freq">
                {topFrequency.map((f) => (
                  <li key={f.diseaseCode}>
                    <span className="freq__name">{f.disease}</span>
                    <span className="freq__bar" aria-hidden="true">
                      <span style={{ width: `${(f.count / maxCount) * 100}%` }} />
                    </span>
                    <span className="freq__count">{f.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      {overview.status === 'error' ? <ErrorState error={overview.error} onRetry={retryAll} compact /> : null}

      {!noRecordsAtAll ? (
        <form className="filters card" onSubmit={(e) => e.preventDefault()} role="search" aria-label={t('history.title')}>
          <div className="filters__search">
            <label htmlFor="h-search" className="field__label">
              {t('history.search')}
            </label>
            <div className="field__control">
              <Search size={16} className="field__icon" aria-hidden="true" />
              <input
                id="h-search"
                type="search"
                className="field__input field__input--icon"
                value={filters.search}
                onChange={setFilter('search')}
              />
            </div>
          </div>
          <div>
            <label htmlFor="h-crop" className="field__label">
              {t('history.crop')}
            </label>
            <select id="h-crop" className="field__input" value={filters.crop} onChange={setFilter('crop')}>
              <option value="">{t('common.all')}</option>
              {CROPS.map((c) => (
                <option key={c} value={c}>
                  {cropLabel(c, t)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="h-from" className="field__label">
              {t('history.from')}
            </label>
            <input id="h-from" type="date" className="field__input" value={filters.dateFrom} max={filters.dateTo || undefined} onChange={setFilter('dateFrom')} />
          </div>
          <div>
            <label htmlFor="h-to" className="field__label">
              {t('history.to')}
            </label>
            <input id="h-to" type="date" className="field__input" value={filters.dateTo} min={filters.dateFrom || undefined} onChange={setFilter('dateTo')} />
          </div>
          <div>
            <label htmlFor="h-sort" className="field__label">
              {t('history.sort')}
            </label>
            <select id="h-sort" className="field__input" value={filters.sort} onChange={setFilter('sort')}>
              <option value="newest">{t('history.newest')}</option>
              <option value="oldest">{t('history.oldest')}</option>
            </select>
          </div>
          {filtersActive ? (
            <button type="button" className="btn btn--ghost btn--sm filters__clear" onClick={() => setFilters(INITIAL_FILTERS)}>
              <X size={16} aria-hidden="true" />
              {t('common.clear')}
            </button>
          ) : null}
        </form>
      ) : null}

      {list.status === 'loading' ? <SkeletonGrid count={6} label={t('common.loading')} /> : null}
      {list.status === 'error' ? <ErrorState error={list.error} title={t('history.error')} onRetry={retryAll} /> : null}

      {noRecordsAtAll ? (
        <EmptyState
          icon={ClipboardList}
          title={t('history.empty.title')}
          body={t('history.empty.body')}
          action={
            <Link to="/analyse" className="btn btn--primary">
              {t('history.empty.cta')}
            </Link>
          }
        />
      ) : null}

      {list.status === 'success' && list.total === 0 && filtersActive ? (
        <EmptyState
          icon={SearchX}
          title={t('history.noMatch.title')}
          body={t('history.noMatch.body')}
          action={
            <button type="button" className="btn btn--secondary" onClick={() => setFilters(INITIAL_FILTERS)}>
              {t('common.clear')}
            </button>
          }
        />
      ) : null}

      {list.status === 'success' && list.items.length > 0 ? (
        <>
          <p className="results-count" aria-live="polite">
            {t('history.showing', { count: list.items.length, total: list.total })}
          </p>
          <div className="grid grid--cards">
            <AnimatePresence>
              {list.items.map((r) => (
                <HistoryCard key={r.analysisId} record={r} />
              ))}
            </AnimatePresence>
          </div>
          {list.error ? <ErrorState error={list.error} onRetry={loadMore} compact /> : null}
          {hasMore ? (
            <div className="load-more">
              <button type="button" className="btn btn--secondary" onClick={loadMore} disabled={list.loadingMore}>
                {list.loadingMore ? <Spinner size={16} /> : null}
                {list.loadingMore ? t('common.loading') : t('common.loadMore')}
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </PageTransition>
  );
}

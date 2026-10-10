import { useTranslation } from 'react-i18next';
import Spinner from './Spinner';
import ErrorState from './ErrorState';

/** Full-screen state shown while the session is being verified, or when verification failed. */
export default function FullPageStatus({ state, error, onRetry }) {
  const { t } = useTranslation();
  return (
    <main className="fullpage">
      {state === 'loading' ? (
        <div className="fullpage__loading">
          <Spinner size={32} label={t('common.loading')} />
          <p>{t('common.loading')}</p>
        </div>
      ) : (
        <ErrorState error={error} title={t('errors.authUnavailableTitle')} onRetry={onRetry} />
      )}
    </main>
  );
}

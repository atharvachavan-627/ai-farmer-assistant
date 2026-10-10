import { AlertTriangle, RotateCw, WifiOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { errorMessage } from '../../utils/errors';

export default function ErrorState({ error, title, onRetry, compact = false }) {
  const { t } = useTranslation();
  const Icon = error?.kind === 'network' ? WifiOff : AlertTriangle;
  return (
    <div className={`state state--error ${compact ? 'state--compact' : ''}`} role="alert">
      <span className="state__icon" aria-hidden="true">
        <Icon size={26} />
      </span>
      {title ? <h2 className="state__title">{title}</h2> : null}
      <p className="state__body">{errorMessage(error, t)}</p>
      {onRetry ? (
        <button type="button" className="btn btn--secondary" onClick={onRetry}>
          <RotateCw size={16} aria-hidden="true" />
          {t('common.retry')}
        </button>
      ) : null}
    </div>
  );
}

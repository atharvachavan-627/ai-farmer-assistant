import { Sprout } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function Logo({ light = false }) {
  const { t } = useTranslation();
  return (
    <span className={`logo ${light ? 'logo--light' : ''}`}>
      <span className="logo__mark" aria-hidden="true">
        <Sprout size={20} />
      </span>
      <span className="logo__text">{t('app.name')}</span>
    </span>
  );
}

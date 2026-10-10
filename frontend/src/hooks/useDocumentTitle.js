import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export function useDocumentTitle(title) {
  const { t } = useTranslation();
  useEffect(() => {
    const app = t('app.name');
    document.title = title ? `${title} · ${app}` : app;
  }, [title, t]);
}

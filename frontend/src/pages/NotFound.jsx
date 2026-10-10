import { Compass } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import EmptyState from '../components/common/EmptyState';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

export default function NotFound() {
  const { t } = useTranslation();
  useDocumentTitle(t('notFound.title'));
  return (
    <main className="fullpage" id="main">
      <EmptyState
        icon={Compass}
        title={t('notFound.title')}
        body={t('notFound.body')}
        action={
          <Link to="/" className="btn btn--primary">
            {t('notFound.cta')}
          </Link>
        }
      />
    </main>
  );
}

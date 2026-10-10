import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './useAuth';
import FullPageStatus from '../components/common/FullPageStatus';

export default function ProtectedRoute() {
  const { status, error, retry } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <FullPageStatus state="loading" />;
  if (status === 'error') return <FullPageStatus state="error" error={error} onRetry={retry} />;
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

import { useState } from 'react';
import { AlertCircle, Info, LogIn } from 'lucide-react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/useAuth';
import AuthShell from '../components/auth/AuthShell';
import TextField from '../components/auth/TextField';
import PasswordField from '../components/auth/PasswordField';
import FullPageStatus from '../components/common/FullPageStatus';
import Spinner from '../components/common/Spinner';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { errorMessage } from '../utils/errors';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { t } = useTranslation();
  useDocumentTitle(t('auth.login.submit'));
  const { status, isAuthenticated, login, sessionExpired, clearSessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from;
  const destination = from ? `${from.pathname}${from.search || ''}${from.hash || ''}` : '/';
  const registered = location.state?.registered;

  const [values, setValues] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showForgot, setShowForgot] = useState(false);

  if (status === 'loading') return <FullPageStatus state="loading" />;
  if (isAuthenticated) return <Navigate to={destination} replace />;

  const validate = () => {
    const next = {};
    if (!values.email.trim()) next.email = t('auth.validation.emailRequired');
    else if (!EMAIL_RE.test(values.email.trim())) next.email = t('auth.validation.emailInvalid');
    if (!values.password) next.password = t('auth.validation.passwordRequired');
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await login({ email: values.email.trim(), password: values.password });
      navigate(destination, { replace: true });
    } catch (err) {
      setApiError(err);
      setSubmitting(false);
    }
  };

  const set = (field) => (e) => {
    setValues((v) => ({ ...v, [field]: e.target.value }));
    if (errors[field]) setErrors((x) => ({ ...x, [field]: undefined }));
    if (sessionExpired) clearSessionExpired();
  };

  return (
    <AuthShell sideText={t('auth.login.side')}>
      <h1 className="auth__title">{t('auth.login.title')}</h1>
      <p className="auth__subtitle">{t('auth.login.subtitle')}</p>

      {sessionExpired ? (
        <div className="alert alert--warning" role="alert">
          <Info size={18} aria-hidden="true" />
          <p>{t('errors.sessionExpired')}</p>
        </div>
      ) : null}
      {registered ? (
        <div className="alert alert--success" role="status">
          <Info size={18} aria-hidden="true" />
          <p>{t('auth.register.success')}</p>
        </div>
      ) : null}
      {apiError ? (
        <div className="alert alert--error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <p>{errorMessage(apiError, t)}</p>
        </div>
      ) : null}

      <form onSubmit={onSubmit} noValidate className="form">
        <TextField
          label={t('auth.email')}
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          value={values.email}
          onChange={set('email')}
          error={errors.email}
          disabled={submitting}
        />
        <PasswordField
          label={t('auth.password')}
          name="password"
          autoComplete="current-password"
          value={values.password}
          onChange={set('password')}
          error={errors.password}
          disabled={submitting}
        />

        <div className="form__row">
          <button type="button" className="link-btn" aria-expanded={showForgot} onClick={() => setShowForgot((s) => !s)}>
            {t('auth.login.forgot')}
          </button>
        </div>
        {showForgot ? (
          <p className="note" role="note">
            {t('auth.login.forgotNote')}
          </p>
        ) : null}

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? <Spinner size={18} /> : <LogIn size={18} aria-hidden="true" />}
          {submitting ? t('auth.login.submitting') : t('auth.login.submit')}
        </button>
      </form>

      <p className="auth__switch">
        {t('auth.login.noAccount')} <Link to="/register">{t('auth.login.createAccount')}</Link>
      </p>
    </AuthShell>
  );
}

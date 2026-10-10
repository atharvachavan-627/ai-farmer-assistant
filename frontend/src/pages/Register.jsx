import { useState } from 'react';
import { AlertCircle, UserPlus } from 'lucide-react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
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

export default function Register() {
  const { t } = useTranslation();
  useDocumentTitle(t('auth.register.submit'));
  const { status, isAuthenticated, register } = useAuth();
  const navigate = useNavigate();

  const [values, setValues] = useState({ name: '', email: '', password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === 'loading') return <FullPageStatus state="loading" />;
  if (isAuthenticated) return <Navigate to="/" replace />;

  const validate = () => {
    const next = {};
    if (!values.name.trim()) next.name = t('auth.validation.nameRequired');
    if (!values.email.trim()) next.email = t('auth.validation.emailRequired');
    else if (!EMAIL_RE.test(values.email.trim())) next.email = t('auth.validation.emailInvalid');
    if (!values.password) next.password = t('auth.validation.passwordRequired');
    else if (values.password.length < 8) next.password = t('auth.validation.passwordShort');
    else if (!/[A-Za-z]/.test(values.password) || !/\d/.test(values.password)) {
      next.password = t('auth.validation.passwordWeak');
    }
    if (!values.confirm) next.confirm = t('auth.validation.confirmRequired');
    else if (values.confirm !== values.password) next.confirm = t('auth.validation.mismatch');
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      const { autoLoggedIn } = await register({
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
      });
      if (autoLoggedIn) navigate('/', { replace: true });
      else navigate('/login', { replace: true, state: { registered: true } });
    } catch (err) {
      setApiError(err);
      setSubmitting(false);
    }
  };

  const set = (field) => (e) => {
    setValues((v) => ({ ...v, [field]: e.target.value }));
    if (errors[field]) setErrors((x) => ({ ...x, [field]: undefined }));
  };

  return (
    <AuthShell sideText={t('auth.login.side')}>
      <h1 className="auth__title">{t('auth.register.title')}</h1>
      <p className="auth__subtitle">{t('auth.register.subtitle')}</p>

      {apiError ? (
        <div className="alert alert--error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <p>{errorMessage(apiError, t)}</p>
        </div>
      ) : null}

      <form onSubmit={onSubmit} noValidate className="form">
        <TextField
          label={t('auth.name')}
          name="name"
          autoComplete="name"
          value={values.name}
          onChange={set('name')}
          error={errors.name}
          disabled={submitting}
        />
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
          autoComplete="new-password"
          value={values.password}
          onChange={set('password')}
          error={errors.password}
          disabled={submitting}
        />
        <PasswordField
          label={t('auth.confirmPassword')}
          name="confirm"
          autoComplete="new-password"
          value={values.confirm}
          onChange={set('confirm')}
          error={errors.confirm}
          disabled={submitting}
        />

        <div className="guidance">
          <p className="guidance__title">{t('auth.guidance.title')}</p>
          <ul>
            <li>{t('auth.guidance.length')}</li>
            <li>{t('auth.guidance.mix')}</li>
            <li>{t('auth.guidance.unique')}</li>
          </ul>
        </div>

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? <Spinner size={18} /> : <UserPlus size={18} aria-hidden="true" />}
          {submitting ? t('auth.register.submitting') : t('auth.register.submit')}
        </button>
      </form>

      <p className="auth__switch">
        {t('auth.register.haveAccount')} <Link to="/login">{t('auth.register.signIn')}</Link>
      </p>
    </AuthShell>
  );
}

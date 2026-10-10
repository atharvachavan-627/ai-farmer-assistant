/** Convert any thrown value into a user-facing, translated message. */
export function errorMessage(err, t) {
  if (!err) return t('errors.generic');
  switch (err.kind) {
    case 'network':
      return t('errors.network');
    case 'unauthorized':
      // Login failures carry a backend message (e.g. wrong credentials); prefer it.
      return err.message || t('errors.unauthorized');
    case 'validation':
      // Backend validation is authoritative - show what it said.
      return err.message || t('errors.validation');
    case 'server':
      return t('errors.server');
    case 'invalid_response':
      return t('errors.invalidResponse');
    default:
      return err.message || t('errors.generic');
  }
}

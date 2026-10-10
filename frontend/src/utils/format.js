const LOCALES = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };

export const formatDateTime = (iso, lang = 'en') => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat(LOCALES[lang] || 'en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
};

export const formatDate = (iso, lang = 'en') => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat(LOCALES[lang] || 'en-IN', { dateStyle: 'medium' }).format(d);
};

export const formatPercent = (value, lang = 'en') =>
  typeof value === 'number'
    ? new Intl.NumberFormat(LOCALES[lang] || 'en-IN', { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : '';

/** Disease/crop names come from the backend; only the crop key is mapped to a local label. */
export const cropLabel = (crop, t) => {
  if (!crop) return t('common.unknown');
  const key = String(crop).toLowerCase();
  const label = t(`common.crop.${key}`, { defaultValue: '' });
  return label || crop;
};

export const LOW_CONFIDENCE_THRESHOLD = 0.7;

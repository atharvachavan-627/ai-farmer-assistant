import { motion, useReducedMotion } from 'framer-motion';
import { AlertOctagon, ArrowLeft, CheckCircle2, ImageOff, ScanLine, ShieldAlert, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function InvalidInputCard({ errorInfo, imageUrl, onReset }) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();

  const errorCode = errorInfo?.errorCode || 'INVALID_INPUT';
  const message =
    errorInfo?.message ||
    t(
      'analyse.validation.defaultMessage',
      'This image does not appear to contain a supported tomato or potato leaf. Please upload a clear photograph of a tomato or potato leaf to continue.'
    );

  const getErrorBadge = (code) => {
    switch (code) {
      case 'INVALID_NON_PLANT_IMAGE':
        return t('analyse.validation.badges.nonPlant', 'Non-Plant Image Detected');
      case 'UNSUPPORTED_PLANT':
        return t('analyse.validation.badges.unsupportedPlant', 'Unsupported Plant Species');
      case 'UNSUPPORTED_CROP_UNCERTAIN':
        return t('analyse.validation.badges.uncertainCrop', 'Uncertain Crop Identity');
      case 'INVALID_NO_LEAF':
        return t('analyse.validation.badges.noLeaf', 'No Suitable Leaf Detected');
      case 'INVALID_IMAGE_QUALITY':
        return t('analyse.validation.badges.quality', 'Insufficient Image Quality');
      case 'INVALID_FILE':
      case 'CORRUPTED_IMAGE':
        return t('analyse.validation.badges.corrupted', 'Corrupted / Unsupported File');
      default:
        return t('analyse.validation.badges.general', 'Input Rejected');
    }
  };

  return (
    <motion.section
      className="result"
      aria-labelledby="invalid-input-title"
      initial={reduce ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.35, ease: 'easeOut' }}
    >
      <div className="result__top card card--invalid-input" style={{ borderColor: 'var(--amber-300)' }}>
        {imageUrl ? (
          <figure className="result__figure">
            <img src={imageUrl} alt={t('analyse.result.imageAlt', 'Uploaded image')} />
            <figcaption>{t('analyse.validation.rejectedImageCaption', 'Rejected uploaded image')}</figcaption>
          </figure>
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'var(--sand-100)',
              borderRadius: 'var(--radius-sm)',
              padding: '32px 16px',
              color: 'var(--ink-soft)',
            }}
          >
            <ImageOff size={48} aria-hidden="true" />
            <p style={{ marginTop: '8px', fontSize: '0.85rem' }}>
              {t('analyse.validation.noPreview', 'Image preview unavailable')}
            </p>
          </div>
        )}

        <div className="result__summary">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              className="tag"
              style={{
                backgroundColor: 'var(--red-50)',
                color: 'var(--red-700)',
                borderColor: '#fca5a5',
                fontWeight: 600,
              }}
            >
              <ShieldAlert size={14} aria-hidden="true" style={{ marginRight: '4px' }} />
              {getErrorBadge(errorCode)}
            </span>
          </div>

          <h2 id="invalid-input-title" className="result__disease" style={{ color: 'var(--red-700)' }}>
            {t('analyse.validation.title', 'Invalid Input')}
          </h2>

          <div
            className="alert alert--warning"
            role="alert"
            style={{
              backgroundColor: 'var(--amber-50)',
              borderColor: 'var(--amber-300)',
              color: 'var(--ink)',
              margin: '12px 0 16px',
              padding: '14px 16px',
            }}
          >
            <AlertOctagon size={20} aria-hidden="true" style={{ color: 'var(--amber-600)', flexShrink: 0 }} />
            <div>
              <strong style={{ display: 'block', color: 'var(--amber-600)', marginBottom: '4px' }}>
                {t('analyse.validation.noAnalysis', 'No disease analysis was performed.')}
              </strong>
              <p style={{ margin: 0, fontSize: '0.92rem' }}>{message}</p>
            </div>
          </div>

          <div
            style={{
              background: 'var(--sand-50)',
              border: '1px solid var(--sand-200)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px 16px',
              marginBottom: '20px',
            }}
          >
            <p
              style={{
                margin: '0 0 8px',
                fontWeight: 600,
                fontSize: '0.88rem',
                color: 'var(--forest-900)',
              }}
            >
              {t('analyse.validation.acceptedCriteriaTitle', 'Valid Image Requirements:')}
            </p>
            <ul
              style={{
                margin: 0,
                paddingLeft: '20px',
                fontSize: '0.86rem',
                color: 'var(--ink-soft)',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <li>
                {t(
                  'analyse.validation.ruleCrops',
                  'Foliage must belong to supported crops: Tomato or Potato.'
                )}
              </li>
              <li>
                {t(
                  'analyse.validation.ruleNoFruitsOrPeople',
                  'Photos of people, animals, objects, flowers, or fruit without leaves are rejected.'
                )}
              </li>
              <li>
                {t(
                  'analyse.validation.ruleQuality',
                  'Image must be in sharp focus, well-lit, and free of extreme glare or blur.'
                )}
              </li>
            </ul>
          </div>

          <div className="result__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={onReset}
              id="upload-another-image-btn"
            >
              <ScanLine size={18} aria-hidden="true" />
              {t('analyse.validation.uploadAnother', 'Upload Another Image')}
            </button>
          </div>
        </div>
      </div>
    </motion.section>
  );
}

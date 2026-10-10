import { useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ImagePlus, RefreshCw, Trash2, UploadCloud } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_MB } from '../../utils/constants';

export default function UploadDropzone({ file, previewUrl, onSelect, onRemove, disabled, error }) {
  const { t } = useTranslation();
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const reduce = useReducedMotion();

  const pick = (files) => {
    if (disabled || !files?.length) return;
    onSelect(files[0]);
  };

  const openPicker = () => inputRef.current?.click();

  const input = (
    <input
      ref={inputRef}
      type="file"
      className="visually-hidden"
      accept={ACCEPTED_IMAGE_TYPES.join(',')}
      aria-label={t('analyse.drop.label')}
      tabIndex={-1}
      onChange={(e) => {
        pick(e.target.files);
        e.target.value = '';
      }}
    />
  );

  if (file && previewUrl) {
    return (
      <motion.div
        className="preview card"
        initial={reduce ? false : { opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: reduce ? 0 : 0.22 }}
      >
        <img src={previewUrl} alt={t('analyse.previewAlt')} className="preview__img" />
        <div className="preview__meta">
          <p className="preview__name" title={file.name}>
            {file.name}
          </p>
          <p className="preview__size">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
          <div className="preview__actions">
            <button type="button" className="btn btn--ghost btn--sm" onClick={openPicker} disabled={disabled}>
              <RefreshCw size={16} aria-hidden="true" />
              {t('analyse.replace')}
            </button>
            <button type="button" className="btn btn--ghost btn--sm btn--danger" onClick={onRemove} disabled={disabled}>
              <Trash2 size={16} aria-hidden="true" />
              {t('analyse.remove')}
            </button>
          </div>
        </div>
        {input}
      </motion.div>
    );
  }

  return (
    <div
      className={`dropzone ${dragging ? 'dropzone--active' : ''} ${error ? 'dropzone--error' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        pick(e.dataTransfer.files);
      }}
    >
      <motion.span
        className="dropzone__icon"
        aria-hidden="true"
        animate={reduce ? undefined : { y: dragging ? -6 : 0, scale: dragging ? 1.08 : 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        {dragging ? <UploadCloud size={32} /> : <ImagePlus size={32} />}
      </motion.span>
      <p className="dropzone__title">{dragging ? t('analyse.drop.active') : t('analyse.drop.title')}</p>
      <p className="dropzone__or">{t('analyse.drop.or')}</p>
      <button type="button" className="btn btn--primary" onClick={openPicker} disabled={disabled}>
        {t('analyse.drop.browse')}
      </button>
      <p className="dropzone__hint">{t('analyse.drop.hint', { size: MAX_IMAGE_MB })}</p>
      {input}
    </div>
  );
}

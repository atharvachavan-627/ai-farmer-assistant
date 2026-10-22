import { useCallback, useEffect, useRef, useState } from 'react';
import { Lightbulb, Sprout } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import PageTransition from '../components/common/PageTransition';
import ErrorState from '../components/common/ErrorState';
import Spinner from '../components/common/Spinner';
import UploadDropzone from '../components/analysis/UploadDropzone';
import AnalysingState from '../components/analysis/AnalysingState';
import ResultCard from '../components/analysis/ResultCard';
import InvalidInputCard from '../components/analysis/InvalidInputCard';
import { analysisService } from '../services/analysisService';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_MB } from '../utils/constants';

export default function Analyse() {
  const { t, i18n } = useTranslation();
  useDocumentTitle(t('nav.analyse'));

  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | loading | success | error | invalid_input
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [invalidError, setInvalidError] = useState(null);
  const [analysedAt, setAnalysedAt] = useState(null);
  const abortRef = useRef(null);

  // Release blob URLs and cancel any in-flight request when leaving the page.
  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => () => previewUrl && URL.revokeObjectURL(previewUrl), [previewUrl]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setFile(null);
    setPreviewUrl(null);
    setFileError(null);
    setResult(null);
    setError(null);
    setInvalidError(null);
    setStatus('idle');
  }, []);

  const onSelect = (selected) => {
    // Clear all previous results and errors immediately
    setResult(null);
    setError(null);
    setInvalidError(null);
    setStatus('idle');
    if (!ACCEPTED_IMAGE_TYPES.includes(selected.type)) {
      setFileError(t('analyse.errors.type'));
      return;
    }
    if (selected.size === 0) {
      setFileError(t('analyse.errors.empty'));
      return;
    }
    if (selected.size > MAX_IMAGE_MB * 1024 * 1024) {
      setFileError(t('analyse.errors.size', { size: MAX_IMAGE_MB }));
      return;
    }
    setFileError(null);
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  };

  const submit = async () => {
    if (!file) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Reset previous states on new submission
    setResult(null);
    setError(null);
    setInvalidError(null);
    setStatus('loading');

    try {
      const data = await analysisService.predict(file, { signal: controller.signal, lang: i18n.resolvedLanguage });
      setResult(data);
      setAnalysedAt(new Date().toISOString());
      setStatus('success');
    } catch (err) {
      if (err?.code === 'ERR_CANCELED' || controller.signal.aborted) return;
      const details = err.details || {};
      const errorCode = details.error_code || details.error?.code || details.code;
      const isValidationError =
        err.status === 422 ||
        err.status === 415 ||
        [
          'INVALID_NON_PLANT_IMAGE',
          'UNSUPPORTED_PLANT',
          'UNSUPPORTED_CROP_UNCERTAIN',
          'INVALID_NO_LEAF',
          'INVALID_IMAGE_QUALITY',
          'INVALID_FILE',
          'CORRUPTED_IMAGE',
          'INVALID_IMAGE_DIMENSIONS',
          'UNSUPPORTED_MEDIA_TYPE',
        ].includes(errorCode);

      if (isValidationError) {
        setInvalidError({
          errorCode: errorCode || 'INVALID_INPUT',
          message: details.message || err.message,
          details,
        });
        setStatus('invalid_input');
      } else {
        setError(err);
        setStatus('error');
      }
    }
  };

  const loading = status === 'loading';

  return (
    <PageTransition className="container page">
      <header className="page__head">
        <h1>{t('analyse.title')}</h1>
        <p>{t('analyse.subtitle')}</p>
      </header>

      {status === 'success' && result ? (
        <ResultCard result={result} imageUrl={previewUrl} analysedAt={analysedAt} onReset={reset} />
      ) : status === 'invalid_input' ? (
        <InvalidInputCard errorInfo={invalidError} imageUrl={previewUrl} onReset={reset} />
      ) : (
        <div className="analyse">
          <div className="analyse__main">
            {loading ? (
              <AnalysingState previewUrl={previewUrl} />
            ) : (
              <UploadDropzone
                file={file}
                previewUrl={previewUrl}
                onSelect={onSelect}
                onRemove={reset}
                disabled={loading}
                error={fileError}
              />
            )}

            {fileError ? (
              <p className="field__error" role="alert">
                {fileError}
              </p>
            ) : null}

            {status === 'error' ? (
              <ErrorState
                error={error}
                title={error?.kind === 'network' ? t('analyse.errors.offline') : t('analyse.errors.failed')}
                onRetry={submit}
                compact
              />
            ) : null}

            {file && !loading ? (
              <button type="button" className="btn btn--primary btn--lg btn--block" onClick={submit}>
                {t('analyse.submit')}
              </button>
            ) : null}
            {loading ? (
              <button type="button" className="btn btn--primary btn--lg btn--block" disabled>
                <Spinner size={18} />
                {t('analyse.analysing')}
              </button>
            ) : null}
          </div>

          <aside className="analyse__side">
            <section className="card side-card">
              <h2 className="side-card__title">
                <Sprout size={18} aria-hidden="true" />
                {t('analyse.supported')}
              </h2>
              <div className="tags">
                <span className="tag">{t('common.crop.tomato')}</span>
                <span className="tag">{t('common.crop.potato')}</span>
              </div>
              <p className="note">{t('analyse.supportedBody')}</p>
            </section>
            <section className="card side-card">
              <h2 className="side-card__title">
                <Lightbulb size={18} aria-hidden="true" />
                {t('analyse.tips.title')}
              </h2>
              <ul className="plain-list">
                <li>{t('analyse.tips.t1')}</li>
                <li>{t('analyse.tips.t2')}</li>
                <li>{t('analyse.tips.t3')}</li>
              </ul>
            </section>
          </aside>
        </div>
      )}
    </PageTransition>
  );
}

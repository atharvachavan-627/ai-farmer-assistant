import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Small data-fetching hook with loading / success / error and retry.
 * `fetcher(signal)` must return a promise. Re-runs when `deps` change.
 * status: 'loading' | 'success' | 'error'
 */
export function useFetch(fetcher, deps = []) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null });
  const [nonce, setNonce] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ status: 'loading', data: s.data, error: null }));
    fetcherRef
      .current(controller.signal)
      .then((data) => setState({ status: 'success', data, error: null }))
      .catch((error) => {
        if (error?.code === 'ERR_CANCELED' || controller.signal.aborted) return;
        setState({ status: 'error', data: null, error });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}

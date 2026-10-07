import { useEffect, useState } from 'react';
export function useMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [enabled, setEnabled] = useState(() => { try { return localStorage.getItem('voiceteam-motion') !== 'off'; } catch { return true; } });
  const [visible, setVisible] = useState(() => !document.hidden);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    const visibility = () => setVisible(!document.hidden);
    query.addEventListener('change', update);
    document.addEventListener('visibilitychange', visibility);
    return () => { query.removeEventListener('change', update); document.removeEventListener('visibilitychange', visibility); };
  }, []);
  function toggle() {
    setEnabled(current => { const next = !current; try { localStorage.setItem('voiceteam-motion', next ? 'on' : 'off'); } catch { /* Optional preference storage. */ } return next; });
  }
  return { enabled: enabled && !reduced, running: enabled && !reduced && visible, reduced, toggle };
}

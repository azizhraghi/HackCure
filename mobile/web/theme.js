/* Shared by the app shell and local demo pages. No network or patient data. */
(() => {
  const key = 'sg.darkMode';
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  function saved() { try { return localStorage.getItem(key); } catch { return null; } }
  function render() {
    const dark = root.dataset.theme === 'dark';
    root.style.colorScheme = dark ? 'dark' : 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.textContent = dark ? '☀ Light mode' : '☾ Dark mode';
      button.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    });
  }
  function apply(dark) {
    root.dataset.theme = dark ? 'dark' : 'light';
    render();
    window.dispatchEvent(new Event('sg-theme-change'));
  }
  function load() { const value = saved(); apply(value === '1' || (value !== '0' && system.matches)); }
  load();
  document.addEventListener('DOMContentLoaded', render);
  document.addEventListener('click', event => {
    if (!(event.target instanceof Element) || !event.target.closest('[data-theme-toggle]')) return;
    const dark = root.dataset.theme !== 'dark';
    try { localStorage.setItem(key, dark ? '1' : '0'); } catch {}
    apply(dark);
  });
  window.addEventListener('storage', event => { if (event.key === key || event.key === null) load(); });
  window.addEventListener('sg-theme-change', render);
  system.addEventListener('change', () => { if (saved() === null) load(); });
})();

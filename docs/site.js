(() => {
  const button = document.querySelector('[data-copy-url]');
  const status = document.querySelector('.copy-status');
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
  if (!button || !status) return;
  button.addEventListener('click', async () => {
    const url = button.dataset.copyUrl;
    status.replaceChildren();
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(url);
      status.textContent = 'Enlace copiado al portapapeles.';
    } catch {
      const label = document.createElement('label');
      label.textContent = 'Copia manualmente este enlace: ';
      const field = document.createElement('input');
      field.type = 'text';
      field.readOnly = true;
      field.value = url;
      field.className = 'copy-fallback';
      label.append(field);
      status.append(label);
      field.focus();
      field.select();
    }
  });
})();

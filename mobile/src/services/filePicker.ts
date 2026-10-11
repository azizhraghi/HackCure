/** Browser upload path; native document selection will be added with the phone build. */
export function pickBrowserFile(accept: string, capture = false): Promise<File | null> {
  const doc = (globalThis as { document?: any }).document;
  if (!doc) return Promise.reject(new Error('Open the web app to upload a file.'));
  return new Promise(resolve => {
    const input = doc.createElement('input');
    input.type = 'file'; input.accept = accept;
    if (capture) input.setAttribute('capture', 'environment');
    input.onchange = () => resolve(input.files?.[0] ?? null);
    input.oncancel = () => resolve(null);
    input.click();
  });
}

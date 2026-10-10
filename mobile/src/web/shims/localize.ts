export function getLocales() {
  const languageTag = typeof navigator === 'undefined' ? 'en-US' : navigator.language || 'en-US';
  return [{ languageTag, languageCode: languageTag.split('-')[0].toLowerCase() }];
}

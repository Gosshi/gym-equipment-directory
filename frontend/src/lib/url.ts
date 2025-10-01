export function encodeOnce(slug: string): string {
  if (slug.length === 0) {
    return slug;
  }

  try {
    const decoded = decodeURIComponent(slug);
    if (encodeURIComponent(decoded) === slug) {
      return slug;
    }
  } catch {
    // If decoding fails, fall back to encoding the original string.
    return encodeURIComponent(slug);
  }

  return encodeURIComponent(slug);
}

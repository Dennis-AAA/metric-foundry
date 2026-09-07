/** Prefix for files in /public when the site is served under GitHub Pages (/repo-name). */
export function publicUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

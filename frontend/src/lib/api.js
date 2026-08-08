/**
 * Single source of truth for the backend origin.
 *
 * Set VITE_API_URL at build time to point a deployed frontend at a deployed
 * backend. Vite inlines import.meta.env.* during the build, so this is resolved
 * statically — there is no runtime lookup and no way to change it after build.
 *
 * The localhost fallback keeps `npm run dev` working with no .env file.
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

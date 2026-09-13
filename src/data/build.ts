/**
 * One timestamp for the whole build: this module is evaluated once per build
 * process, so every page stamps the same dateModified instead of each page
 * frontmatter taking its own clock reading a few milliseconds apart.
 */
export const built = new Date().toISOString();

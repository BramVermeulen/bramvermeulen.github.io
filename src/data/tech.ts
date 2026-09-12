/**
 * Official homepages for every technology named on the site.
 *
 * Single source of truth so a technology reads the same wherever it shows up:
 * a skill chip, a project tag, the stack list, or a mention in prose. Keys are
 * the exact display names, and `TechName` keeps the lookups typed, so a typo in
 * a skill list or a tag fails `astro check` instead of rendering a dead link.
 */
export const techLinks = {
  '.NET': 'https://dotnet.microsoft.com',
  Angular: 'https://angular.dev',
  Astro: 'https://astro.build',
  Azure: 'https://azure.microsoft.com',
  'C#': 'https://learn.microsoft.com/dotnet/csharp/',
  Docker: 'https://www.docker.com',
  'GitHub Actions': 'https://github.com/features/actions',
  'GitHub Pages': 'https://pages.github.com',
  Go: 'https://go.dev',
  Grafana: 'https://grafana.com',
  Kubernetes: 'https://kubernetes.io',
  Linux: 'https://www.kernel.org',
  MongoDB: 'https://www.mongodb.com',
  MySQL: 'https://www.mysql.com',
  Nix: 'https://nixos.org',
  NixOS: 'https://nixos.org',
  'Node.js': 'https://nodejs.org',
  Odoo: 'https://www.odoo.com',
  PostgreSQL: 'https://www.postgresql.org',
  Prometheus: 'https://prometheus.io',
  Python: 'https://www.python.org',
  'SQL Server': 'https://www.microsoft.com/sql-server',
  'Tailwind CSS': 'https://tailwindcss.com',
  TypeScript: 'https://www.typescriptlang.org',
} as const satisfies Record<string, string>;

export type TechName = keyof typeof techLinks;

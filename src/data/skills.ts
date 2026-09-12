import type { TechName } from './tech';

/**
 * The technologies listed under Skills, grouped by how much mileage they have.
 *
 * Shared between the chips rendered on the homepage and the `knowsAbout` list
 * in the Person JSON-LD, so what a machine reads can never drift from what a
 * visitor sees. Names are `TechName`, so every skill is guaranteed a link.
 */
export const skillGroups = [
  {
    group: 'Running in production',
    items: [
      'Python',
      'Odoo',
      'PostgreSQL',
      'TypeScript',
      'Linux',
      'Docker',
      'NixOS',
    ],
  },
  {
    group: 'Battle-tested',
    items: [
      'Go',
      'C#',
      '.NET',
      'Angular',
      'Node.js',
      'Kubernetes',
      'SQL Server',
      'MySQL',
      'MongoDB',
      'Prometheus',
      'Grafana',
    ],
  },
] as const satisfies readonly { group: string; items: readonly TechName[] }[];

/** Every skill name, flattened, for structured data. */
export const skillNames: readonly TechName[] = skillGroups.flatMap(
  ({ items }) => items,
);

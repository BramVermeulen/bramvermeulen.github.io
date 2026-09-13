/**
 * The facts about me that both the prose and the structured data state.
 *
 * Said once here so a role or employer change is a single edit that moves the
 * prose and the JSON-LD together, instead of leaving a machine reading one
 * story while a reader gets another.
 */
export const profile = {
  name: 'Bram Vermeulen',
  jobTitle: 'Full-Stack Engineer',
  employer: {
    name: 'Steen Elektriciteit',
    url: 'https://www.steen-elektriciteit.be/',
  },
  /** Profiles that are provably the same person, for `sameAs`. */
  sameAs: [
    'https://github.com/BramVermeulen',
    'https://www.linkedin.com/in/vermeulen-bram/',
  ],
  siteUrl: 'https://bramvermeulen.github.io',
} as const;

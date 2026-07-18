# bramvermeulen.github.io

My personal portfolio site, live at [bramvermeulen.github.io](https://bramvermeulen.github.io/).

Built with [Astro](https://astro.build) and [Tailwind CSS](https://tailwindcss.com). The only JavaScript on the site is the theme toggle (light/dark/system).

## Development

The repo ships a Nix flake with the Node toolchain, so no global Node install is needed:

```sh
nix develop
npm install
npm run dev
```

The dev server runs at `localhost:4321`. Use `npm run build` for a production build in `dist/`.

## Deployment

Every push to `main` builds and publishes the site to GitHub Pages via the workflow in `.github/workflows/deploy.yml`.

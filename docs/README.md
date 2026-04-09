# BookSmart GitHub Pages

This folder contains a static GitHub Pages site for browsing textbook accuracy results.

## Refresh the site data

From the repo root:

```bash
python3 "Figures+Tables/export_accuracy_site_data.py"
```

That rewrites:

```text
docs/data/accuracy-site-data.json
```

## Local preview

From the repo root:

```bash
python3 -m http.server 4173 --directory "docs"
```

Then open:

```text
http://127.0.0.1:4173
```

## Publish with GitHub Pages

In GitHub repository settings:

1. Open **Pages**.
2. Set **Source** to **Deploy from a branch**.
3. Choose your default branch.
4. Choose the `/docs` folder.

After that, pushing changes to `docs/` will update the site.

# Field Atlas

A UK MeshCore terrain planner. Enter a postcode, choose a public mesh node, and compare the terrain between the two antennas. Both antenna heights are adjustable. A clear profile is not a reception guarantee.

## Run locally

Use Python 3.11+ and obtain the **original `UK-MeshCore-Atlas.zip` data distribution** from the project owner. This source repository deliberately does not publish node snapshots, postcode databases, or terrain archives in Git. It will not run without these files. This is a Python web app, not a GitHub Pages site.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/install-data.py /path/to/UK-MeshCore-Atlas.zip
printf '{}\n' > static/operator-heights.json  # new install only; never overwrite existing reports
.venv/bin/python server.py
```

Visit http://127.0.0.1:8080. If migrating an existing installation instead, copy its `data/` and `static/operator-heights.json` (if present) privately; do not commit them. No third-party credentials are required for the bundled terrain lookup. Northern Ireland postcode lookup, fallback postcode lookup, catalogue refresh, and optional street tiles need internet.

## Node catalogue & heights

The refresh button retrieves a full public snapshot, selects UK records by boundary and replaces the catalogue. Successful refreshes are cached for 15 minutes per server process. Missing antenna heights are labelled as assumptions, not inferred from ground elevation.

Run the administration tools from the repository root. The height interface is already integrated; you do not need to run its installer. `python3 tools/field-atlas-heights.py list` lists saved reports. `python3 tools/field-atlas-heights.py set "NODE NAME" METRES` records a confirmed height above local ground. The operator store contains public-facing metadata: do not add private operator details. For an authorised CSV with `public_key,height_agl_m`, run `python3 tools/import-meshmapper-heights.py file.csv` to preview exact-key matches. Use `--apply` only after review. No MeshMapper heights are supplied or scraped.

## Deploy

Use Gunicorn behind Nginx. Adapt `deploy/field-atlas.service` to your service account and install location. The service user must be able to read the app and write `data/` for refreshes. Install the unit in `/etc/systemd/system/`, then `systemctl daemon-reload` and `systemctl enable --now field-atlas`. `deploy/nginx.example.conf` contains the proxy location for an existing TLS site. Leave Gunicorn on loopback. Keep certificates, private keys and backups outside Git. Do not install this second service alongside an existing atlas already listening on port 8000.

For data sources, model limitations and attribution see [data notes](docs/original-notes.md). Vendored JavaScript licences are under `static/`. No blanket licence is asserted over third-party datasets.

## Compare repeaters and keep field notes

Set a postcode and select **Compare nearby repeaters**. The app checks the nearest 20 repeater records (independent of directory filters), using the selected origin antenna height and each repeater’s reported height or a 6 m assumption. Worst sampled clearance includes the endpoints and uses the same effective-Earth model as the single-path chart. Higher minimum clearance ranks first, then shorter distance. This is not an RF coverage ranking. Click a row to inspect the path; change your origin height and reopen to rerank.

**Field-test log** records a manual observation against the selected profile. Direct replies, relayed replies and unknown routes are distinct. Entries include postcode, heights, node public key, predicted clearance and timestamp. The log is held in local browser storage, not the catalogue or server. JSON export includes the postcode, so review it before sharing.

Run `node --test tests/field-tools.cjs` to verify clearance calculations.

For an optional end-to-end test, install the data pack, run `python -m pip install playwright` and `python -m playwright install --with-deps chromium` in the app environment, then run `python tests/browser_smoke.py` from the repository root. It starts a temporary loopback test server and uses a disposable browser context; no observations are posted or imported.

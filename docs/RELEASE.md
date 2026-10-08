# Publishing and maintaining the release

## GitHub

Upload the **G1SPEI code directory**, not its parent containing parameters and
validation output. The `.gitignore` excludes large rasters and runtime products.
The repository includes an MIT license, author contact, citation metadata,
installable package, command-line interface, bilingual guides, tests and CI.

```sh
git init
git add .
git status
git commit -m "Prepare G1SPEI rapid production release candidate"
```

Review `git status` before adding your actual GitHub remote and pushing. No remote
has been created by this local preparation. The author should choose the repository
name and visibility. A supplied source ZIP can also be uploaded through GitHub's UI.

## Zenodo

1. Create a parameter-data deposit and upload the prepared parameter archives,
   `manifest.json`, `archives.sha256`, and parameter README. The raw rasters need not
   also be uploaded because the archives contain them without loss.
2. Enter Zhenheng Xu and xuzh@nercita.org.cn. Describe the 1970–2000 downscaling
   climatologies separately from the 1951–2025 SPEI calibration/heat index.
3. Select the data license after confirming source redistribution terms. The
   code's MIT license does not automatically license these rasters.
4. Reserve/publish the real parameter DOI, then add it to `docs/PARAMETERS.md` and
   link it from the GitHub README. If appropriate, archive the code release with
   its own software DOI. These are distinct research objects.
5. Test download, extraction and `verify-parameters` from a separate location.

The parameter bundle is deliberately independent of the much larger 1951–2025
monthly product archive. Software users need the parameter bundle plus new monthly
forcing, not the full historical G1SPEI dataset.

## Before promoting rc1 to a stable scientific release

- Review the executed validation report and the low-sigma coverage results.
- State the selected QC threshold/profile in the paper and release metadata.
- Quantify the historical annual-PET versus rapid climatological-PET difference
  for the intended operational use; full-grid execution alone is not this validation.
- Confirm the parameter-data license and insert the actual DOI/links.
- Run CI on the chosen public repository; local Windows tests do not establish
  that the prepared Linux CI job has already executed.

## Monthly operation

Once a complete new forcing pair is available, run the CLI for that month with
explicit units, parameter version and a new output path. Inspect `run.json` and QA.
Schedule this command using the user's own scheduler if unattended execution is
needed. The package does not scrape credentials, submit CDS requests or silently
replace provisional data. Keep previous outputs when forcing revisions are processed.

Changes to climatology, fitting baseline, PET convention or quality thresholds
must be versioned; do not silently overwrite the published parameter maps.

# Release checklist for SoftwareX submission

Use this checklist before creating the `v1.0.0` manuscript release.

## Repository

- [ ] Confirm `reflectogen.py --version` reports `ReflectoGen 1.0.0`.
- [ ] Run `pytest -q` from a clean environment.
- [ ] Run `bash examples/example_commands.sh` from the repository root.
- [ ] Confirm `README.md` examples are copy-pasteable.
- [ ] Confirm `LICENSE` is MIT and copyright names are correct.
- [ ] Confirm `CITATION.cff` names, title, version, and repository URL are correct.
- [ ] Confirm `.zenodo.json` metadata are correct.
- [ ] Remove unwanted generated output files before tagging.

## GitHub release

```bash
git status
git add .
git commit -m "Prepare ReflectoGen v1.0.0 manuscript release"
git tag -a v1.0.0 -m "ReflectoGen v1.0.0"
git push origin main
git push origin v1.0.0
```

Then create a GitHub release from the `v1.0.0` tag.

## Zenodo archive

- [ ] Enable Zenodo archiving for the GitHub repository.
- [ ] Archive the GitHub `v1.0.0` release.
- [ ] Copy the generated DOI.
- [ ] Add the DOI to `README.md`, `CITATION.cff`, and the manuscript reference list.
- [ ] Update the SoftwareX code metadata table with the DOI landing page.

## Manuscript updates

- [ ] Replace placeholder Code availability text.
- [ ] Replace placeholder software citation with the archived release DOI.
- [ ] Add Data availability statement.
- [ ] Add CRediT author statement.
- [ ] Add funding role statement.
- [ ] Add generative AI declaration if applicable.
- [ ] Keep highlights under 85 characters each.

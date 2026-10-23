# Offline demo

From the isolated workspace root, run:

```bash
bash product/organize-appai/scripts/demo.sh
```

The script validates its absolute workspace and disposable targets before modification,
copies synthetic fixtures into `artifacts/demo/working`, explains the sample configuration,
runs traced simulation, diagnoses one matching and one rejected file, creates and validates
an offline deterministic proposal, simulates that proposal, and shows resident status.

No paid provider, network access, or credentials are required. The original fixture tree
and both pristine source clones are fingerprinted/checked and left unchanged. Generated
output is confined to `artifacts/demo` and `.organize-appai/proposals` under the workspace.

On Windows, run the script in Git Bash. The AppAI build disables Rich emoji substitution so
ordinary legacy PowerShell code pages remain usable; `--format JSONL` is also available for
machine-oriented `run`/`sim` output.

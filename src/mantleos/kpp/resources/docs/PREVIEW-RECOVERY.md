# Preview recovery and transport

module-disable --workspace WS --id ID [--cascade] withdraws an extension and enabled dependents. module-enable restores retained pinned source after its dependencies. Active changes clear acceptance. The mounted Body preserves current draft/selection through managed cleanup; arbitrary unregistered effects are outside the contract.

Native writer locking is released by the OS on exit. Pending metadata identifies interruption. recover-writer --workspace WS --reviewed refuses live writers and validates committed pins. Review interrupted actions before retrying; recovery never promotes orphaned source.

For explicit origin/host recovery, save window.KPP.exportState() as UTF-8 JSON using the browser console. kpp.browser-state/1 includes profile json-body/1, recipe/source fingerprint and Body snapshot.

```powershell
python -m kpp preview-export --workspace workspaces/notes --out notes.zip --browser-state notes-state.json
python -m kpp preview-import --bundle notes.zip --output workspaces/restored-notes
python -m kpp serve --workspace workspaces/restored-notes --port 8766
```

Receiving runtime restores the checkpoint before activating modules. Without --browser-state, bundles carry sources/evidence, not live browser data. Private data belongs in user-selected private outputs.

Archives are deterministic, bounded to 160 files/16 MiB, pin checked, and refuse duplicate/unsafe paths, symlinks or existing destinations. Imports stage and validate before publishing without execution. A new workspace begins BUILDING without operative approval. History and GUI records remain provenance, not current authority. Review imported code before serving.

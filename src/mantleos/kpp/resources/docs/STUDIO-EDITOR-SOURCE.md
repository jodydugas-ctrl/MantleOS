# Owner-reviewed editor source

This is an incremental part of the full Community Chase, not a complete editor
backend or a change to its acceptance scope. Node-RED remains the Body.

Within the existing Community design, `BH-COMMAND` receives the explicitly
reviewed profile, `N-HOST` owns the loaded presentation snapshot, and
`WH-CONTRACT` checks source/path/size boundaries before admission. The same
canonical Anchor applications describe those responsibilities; this JavaScript
loader is host integration, not a new executable Anchor profile. Asset admission
does not satisfy the separate workflow, effects or acceptance obligations.

The optional `examples/anchor-studio/editor-assets.cjs` loader accepts a locally
provisioned `n8n-editor-ui` **2.46.4** package. It does not install dependencies,
run package scripts, start an n8n server, configure a provider, or grant effects.
The version is the existing pinned Chase reference, not a claim about the latest
upstream release. Assets are not bundled in either GitHub project.

After reviewing the source and its applicable license, use the project-local
Node executable with the following commands. Choose an unused profile file:

```console
node examples/anchor-studio/editor-assets.cjs pin --package LOCAL_PACKAGE --profile NEW.json --revision 261663556d98c9502663f6618edd8edd537e5688 --reviewed
node examples/anchor-studio/editor-assets.cjs check --package LOCAL_PACKAGE --profile NEW.json
node --test examples/anchor-studio/editor-assets.test.cjs
```

`studio.editor-source/1` binds package identity, declared upstream revision,
every file below `dist`, and the exact `package.json`, `LICENSE.md`, and
`LICENSE_EE.md` bytes. The revision is owner-supplied provenance; this utility
does not establish that an npm package was reproducibly built from that commit.
Hashes establish integrity, not authentication, license permission, user
identity, execution support, or Baker acceptance. Profiles contain no local
paths, credentials, resident identity, or private memory.

On load, the loader validates the complete profile, rejects changed/missing or
extra files, links, special files, ambiguous case-only names and unsafe paths,
then retains a private snapshot of the verified bytes. The default limits are
2,048 files, 10 MiB per file, 64 MiB in total, and a 1 MiB profile. Directory
traversal is also bounded. A newly opened session rechecks the complete source;
an already loaded snapshot remains unchanged if disk contents or caller-owned
objects subsequently change. These checks are a cooperating owner-local
boundary, not protection against an administrator or a compromised Node process.

`loadSnapshot` exposes copied asset bytes and original license notices. Its
`index()` prepares the known root-path placeholders, inserts fixed same-origin
`rest` endpoint metadata and generates a fresh nonce. JavaScript and CSS
root-path placeholders are expanded in memory. The installed package is never
rewritten. A host must apply its own navigation, origin, authorization, HTTP
content-type, error and effect boundaries before serving these bytes. Importing
this module or pinning a profile never activates an editor in the current
launcher. The existing Studio and ordinary Node-RED editor remain unchanged.

The synthetic tests cover deterministic admission, required review, immutable
snapshots, notices, same-length changes, missing/extra source, profile changes,
path attacks, junction/symlink rejection, limits, and read-only checks in fresh
receiving processes. The fixtures contain synthetic notices and establish no
upstream licensing or full n8n behavioral claim. Real browser editing, backend
execution, expressions, triggers, credentials, settings and current-candidate
cumulative verification still require their separate recipe evidence.

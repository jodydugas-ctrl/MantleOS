# Mantle Paint — a KPP test bake

A working local HTML Canvas paint app, with **Windows XP Paint as its Chase
target**. It is Bio-Software: a useful deterministic Body with founding material,
experience and recovery. It is neither an AppAI nor an autonomous agent. No MIND,
network, account, package download or model call is required to use it.

## Open the app

From the repository with `PYTHONPATH=src`:

```console
python examples/paint/build.py --output .work/my-paint
```

Open `.work/my-paint/Mantle-Paint.html` in a modern browser or a host that can
render interactive HTML/Canvas. This is a complete single file. The adjacent
`Mantle-Paint.anchor` is the complete portable thought, including its receiver
bridge and exact HTML/Python targets. The Python target emits the app's HTML;
it is not a second graphical Paint implementation. The build proves an isolated
receiver needs no MantleOS installation and preserves every UTF-8 byte.

To preview the editable source instead:

```console
python -m http.server 8877 --bind 127.0.0.1 --directory examples/paint
```

Open `http://127.0.0.1:8877/`. Stop the server with Ctrl+C. The delivered single
HTML file works directly from disk; browser storage and downloads remain subject
to the receiving host's support and permissions. Opening a new copy creates a
fresh identity unless you explicitly restore an organism.

## Use it

Choose a tool on the left and a color below. Left-click sets/draws the foreground;
right-click uses the background. Double-click a color to edit it. The sixteen
tools include masked free-form and rectangular selection, eraser/color eraser,
fill, color picker, magnifier, pencil, brush, airbrush, text, line, two-bend curve,
rectangle, polygon, ellipse and rounded rectangle.

Drag to draw. Curve takes an initial line and up to two bend gestures. Polygon
takes an initial side and further corners; double-click or Enter closes it.
Text takes a dragged box; Ctrl+Enter commits it. Shift constrains lines and shapes.
Selected pixels can move; Shift-drag copies. Copy/cut/paste use an app-private
clipboard. Paste From imports a local image without needing system clipboard
access. Help Topics lists keyboard operations.

Image commands support resize, stretch/skew, flips, rotations, inversion and
clear. Zoom/grid do not resample stored pixels. Open supports bounded PNG, JPEG,
GIF and uncompressed 24/32-bit BMP. Save As produces PNG, JPEG or 24-bit BMP.
Only the first frame of an imported animated GIF is painted.

## What makes it living software

- A source-defined founding PRIMER and separate instance identity.
- Deterministic editing without cognition or an external provider.
- Experience appended in a hash-linked ledger. Undo changes executable image
  state without deleting past experience.
- Automatic recovery after committed edits when browser storage is available.
  A new page offers recovery instead of silently replacing the user's session.
- Explicit stasis/resumption. No OS service or background organism is installed.
- File → Save Organism exports pixels, identity, PRIMER and experience as
  `mantle.paint-organism/1`. Open Organism verifies before replacing the active
  Body. This is an application checkpoint, not a general MantleOS cartridge.

PNG/JPEG/BMP picture files contain the picture only. They are not Chroma identity
carriers. The Anchor thought carries the application with blank initial experience;
an organism JSON carries an experienced instance. Checksums detect changes, not
trusted authorship. File content never supplies extra authority or executable code.

The document is capped at 2 million pixels and 2,048 pixels per side. Undo holds
at most 16 snapshots / 32 MB. Canonical experience is not pruned; its 4,096-record
limit produces an explicit warning. Large pictures may exceed browser storage
quotas; drawing and picture export remain available. Export organism files before
relying on browser-local recovery. The app does not promise crash-atomic durable
storage or a full event-replay reconstruction of every pixel from the ledger.

## Repeat the checks

```console
node --test examples/paint/test_raster.cjs
python -m unittest discover -s tests -p test_paint.py -v
python -m unittest discover -s tests -v
```

Node 18+ is optional developer tooling, not an app or Python core dependency.
For browser checks, serve the source and open
`http://127.0.0.1:8877/browser-tests.html`, then click **Run browser checks**.
The fixture uses its own recovery key and synthetic data. Its authored DOM events
and Canvas checks are distinguished from the separately performed real pointer,
keyboard, file-picker and Save As checks. [verification.json](verification.json)
records source identities, actual counts and remaining gaps.

The supplied KPP 1.0.1-dev archive was tested separately in an ignored extraction.
Its recipe validation, Pantry resolution, workspace, source Scan, Functional
Graph, coverage, Chase priorities, doctor and refusal to complete an unapproved
bake were exercised. The shared MantleOS binding retains this recipe's obligations
as attributes on the existing Neutral Anchor. No second Anchor system is added.

## Chase status: useful app; native comparison still open

The contemporary [XP Paint guide](https://users.sch.gr/edimitriad/images/Zografiki/A_Guide_to_Microsoft_Paint_XP.pdf)
is a behavioral reference for the classic interface, raster workflow and tools.
It is linked, not redistributed. A direct byte download failed certificate
validation; no fictitious PDF hash or native-executable pin is recorded.

No trusted XP executable was supplied or run. Native GDI pixels, exact font
metrics, Windows clipboard/OLE, printing/page setup, wallpaper, TIFF/GIF export,
indexed/compressed BMP and floating/detachable toolbar fidelity are not certified.
Browser text is antialiased; the raster drawing tools use their own pixel
algorithms. Curve control geometry and selection clipping can differ from GDI.
These are open Chase work, not silently claimed as native equivalence.

The nine required obligations include **native-xp-parity**. KPP remains
`BUILDING`, with no Baker attestations; `complete` correctly refuses. Automated
tests provide evidence, never the operator's acceptance. The missing native
reference does not prevent using the delivered app.

The implementation and icons are original project source. Microsoft product
names identify the comparison target; no Microsoft executable, icon asset,
wallpaper or proprietary implementation is included.

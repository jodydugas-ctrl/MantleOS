import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const BASE = process.env.BASE_URL || "http://localhost:8765";
const PLAYWRIGHT_IMPORT = process.env.PLAYWRIGHT_MODULE_PATH
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE_PATH).href
  : "playwright";
const { chromium } = await import(PLAYWRIGHT_IMPORT);

function isExternal(url) {
  const parsed = new URL(url);
  return !["localhost", "127.0.0.1", "::1"].includes(parsed.hostname);
}

async function waitForBody(page) {
  await page.goto(`${BASE}/notepad_appai/?cb=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForFunction(() => Boolean(window.NotepadAppAI), { timeout: 10000 });
  await page.evaluate(() => {
    localStorage.setItem("mantle.notepad.ledger.v1", JSON.stringify([
      { id: "legacy-1", timestamp: "2026-06-25T00:00:00.000Z", type: "buffer_changed", detail: { chars: 1 } },
      { id: "legacy-2", timestamp: "2026-06-25T00:00:01.000Z", type: "buffer_changed", detail: { chars: 2 } }
    ]));
  });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => Boolean(window.NotepadAppAI), { timeout: 10000 });
}

async function runChecks(page) {
  const failures = await page.evaluate(async () => {
    const fails = [];
    const body = window.NotepadAppAI;
    const editor = document.getElementById("editor");
    const selection = () => editor.value.slice(editor.selectionStart, editor.selectionEnd);
    const expect = (condition, message) => { if (!condition) fails.push(message); };

    try {
      const declaration = body.readDeclaration();
      const organMap = body.readOrganMap();
      const evidenceIndex = body.readHostEvidenceIndex();
      const guiCoverage = body.readGuiNerveCoverage();
      const parity = body.readParityMatrix();
      expect(declaration.default_model === "none in Phase 1", "AppAI declaration does not disable models");
      expect(organMap.organs && organMap.organs.Brain && /dormant/i.test(organMap.organs.Brain.join(" ")), "Organ map lacks dormant Brain");
      expect(evidenceIndex.kind === "HOST_EVIDENCE_INDEX", "Resident host evidence index missing");
      expect(evidenceIndex.schema_version === "mantle-host-evidence-v2", "Resident host evidence index is not v2");
      expect(evidenceIndex.local_first_consultation === true, "Resident consultation is not local-first");
      expect(evidenceIndex.consultation_contract.text_commit_policy.includes("HOST_TEXT_COMMIT"), "Text commit policy missing from resident evidence");
      expect(evidenceIndex.control_surfaces.some((control) => control.control === "saveFile"), "Body save control evidence missing");
      expect(guiCoverage.kind === "GUI_NERVE_COVERAGE", "GUI nerve coverage missing");
      expect(guiCoverage.schema_version === "mantle-gui-nerve-coverage-v2", "GUI nerve coverage is not v2");
      expect(guiCoverage.total_surfaces >= 30, "GUI nerve coverage omitted visible controls");
      expect(guiCoverage.contract.no_silent_gui_omission === true, "GUI nerve coverage lacks no-silent-omission contract");
      expect(guiCoverage.contract.text_commit_policy.includes("HOST_TEXT_COMMIT"), "GUI coverage lacks text commit contract");
      expect((guiCoverage.maintenance_findings || []).length === 0, "GUI data-action handler gap exists");
      expect(guiCoverage.surfaces.filter((surface) => surface.surface_type === "action").every((surface) => surface.vcw_status === "verified_body_operation"), "Not every data-action has a Body handler");
      expect(guiCoverage.surfaces.some((surface) => surface.id === "editor" && surface.commit_policy === "submit_or_blur"), "Editor surface lacks submit_or_blur commit policy");
      const structureAnswer = body.consultHostEvidence("How is this software structured?");
      expect(structureAnswer.includes("Substrate: browser-javascript"), "Structure answer did not use resident evidence");
      expect(structureAnswer.includes("Limbs"), "Structure answer omitted organ map");
      const controlAnswer = body.consultHostEvidence("What functions do you have?");
      expect(controlAnswer.includes("Observed Body controls"), "Control answer did not use resident evidence");
      expect(controlAnswer.includes("GUI surfaces"), "Control answer omitted GUI nerve coverage");
      expect(controlAnswer.includes("Action Execution Proof"), "Control answer omitted proof requirement");
      expect(controlAnswer.includes("HOST_TEXT_COMMIT"), "Control answer omitted text commit policy");
      expect(controlAnswer.includes("plain-English host-surface requests"), "Control answer omitted conversational MIND dispatch policy");
      expect(controlAnswer.includes("working surfaces are app-specific anatomy"), "Control answer omitted app-specific working-surface policy");
      expect(controlAnswer.includes("tabs are not universal slash commands"), "Control answer implied app tabs are global commands");
      expect(controlAnswer.includes("creative/generative content must be authored by the resident MIND"), "Control answer omitted MIND-owned creative work policy");
      expect(controlAnswer.includes("resident VCW resets must be explicit"), "Control answer omitted explicit reset policy");
      expect(body.getLedger().some((entry) => entry.type === "resident_consultation"), "Resident consultation was not logged");
      expect(parity.length >= 11 && parity.every((row) => row.status === "PASS"), "Parity matrix is incomplete or not green");
      expect(body.phase1NoModelCalls() === true, "Phase-1 no-model policy missing");
      expect(body.brainStatus().mind === "dormant" && body.brainStatus().mayMutate === false, "Brain affordance is not dormant");
      expect(!body.getLedger().some((entry) => entry.type === "buffer_changed"), "Legacy buffer_changed rows survived ledger migration");
      expect(body.getLedger().some((entry) => entry.type === "ledger_migration" && entry.detail.count === 2), "Legacy ledger migration summary missing");

      body.setText("", "typing.txt", true);
      const beforeTyping = body.getLedger().length;
      editor.focus();
      for (const value of ["a", "ab", "abc"]) {
        editor.value = value;
        editor.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const duringTyping = body.getLedger().slice(beforeTyping);
      expect(!duringTyping.some((entry) => entry.type === "buffer_changed" || entry.type === "buffer_committed" || entry.type === "HOST_TEXT_COMMIT"), "Focused typing wrote noisy buffer ledger entries");
      editor.blur();
      await new Promise((resolve) => setTimeout(resolve, 50));
      const afterBlur = body.getLedger().slice(beforeTyping);
      const blurCommits = afterBlur.filter((entry) => entry.type === "HOST_TEXT_COMMIT");
      expect(!afterBlur.some((entry) => entry.type === "buffer_changed"), "Legacy per-keystroke buffer_changed entries still exist");
      expect(
        blurCommits.length === 1
          && blurCommits[0].detail.chars === 3
          && blurCommits[0].detail.commit_policy === "submit_or_blur"
          && blurCommits[0].detail.commit_boundary === "editor_blur",
        "Editor blur did not write one clean HOST_TEXT_COMMIT"
      );

      body.setText("draft text", "draft.txt", false);
      expect(body.isDirty() === true, "edit buffer did not become dirty");
      body.setConfirmAdapter(() => false);
      expect(await body.newFile() === false, "New ignored a rejected unsaved-change prompt");
      expect(editor.value === "draft text", "Rejected New changed the buffer");
      body.setConfirmAdapter(() => true);
      expect(await body.newFile() === true, "New did not proceed after accepted unsaved-change prompt");
      expect(editor.value === "" && body.isDirty() === false, "New did not clear and save-clean the buffer");

      const file = new File(["alpha beta\nalpha beta"], "sample.txt", { type: "text/plain" });
      expect(await body.loadTextFile(file) === true, "Open failed for a valid text File");
      expect(editor.value === "alpha beta\nalpha beta", "Open did not load exact text");
      expect(body.isDirty() === false, "Open did not mark loaded text clean");

      expect(body.findNext("beta", { matchCase: true }) === true, "Find Next failed");
      expect(selection() === "beta", "Find Next did not select the match");
      expect(body.replaceCurrent("beta", "BETA", { matchCase: true }) === true, "Replace current failed");
      expect(editor.value.startsWith("alpha BETA"), "Replace current changed the wrong text");
      expect(body.replaceAll("alpha", "ALPHA", { matchCase: true }) === 2, "Replace All count was wrong");
      expect(editor.value === "ALPHA BETA\nALPHA beta", "Replace All produced unexpected buffer");

      const lineTwoPos = body.goToLine(2);
      expect(lineTwoPos === editor.value.indexOf("\n") + 1, "Go To line placed caret incorrectly");
      expect(body.toggleWordWrap(true) === true, "Word Wrap did not toggle on");
      expect(editor.classList.contains("word-wrap"), "Word Wrap class missing");

      const writes = [];
      body.setSaveAdapter(async ({ mode, text, fileName }) => {
        writes.push({ mode, text, fileName });
        if (mode === "saveAs") return { fileName: "saved-as.txt" };
        return { fileName: fileName || "sample.txt" };
      });

      body.setText("saved\nbody", "sample.txt", false);
      expect(await body.saveFile() === true, "Save failed through Body/Limb adapter");
      expect(writes.at(-1).mode === "save" && writes.at(-1).text === "saved\nbody", "Save wrote unexpected payload");
      expect(body.isDirty() === false, "Save did not mark buffer clean");

      body.setText("save as body", "sample.txt", false);
      expect(await body.saveAsFile() === true, "Save As failed through Body/Limb adapter");
      expect(writes.at(-1).mode === "saveAs" && writes.at(-1).fileName === "sample.txt", "Save As call was malformed");
      expect(document.getElementById("titleText").textContent.includes("saved-as.txt"), "Save As did not update document name");

      const badFile = { name: "locked.txt", size: 3, text: async () => { throw new Error("locked file"); } };
      expect(await body.loadTextFile(badFile) === false, "Bad/locked file did not fail gracefully");
      expect(body.getLedger().some((entry) => entry.type === "immune_event"), "Immune event missing for bad file");

      const proofs = body.getProofs();
      expect(proofs.some((p) => p.ok && p.method.includes("save")), "Save proof missing");
      expect(proofs.some((p) => p.ok && p.method.includes("save-as")), "Save As proof missing");
      expect(proofs.some((p) => p.ok && p.method === "File.text"), "Open proof missing");
      expect(proofs.some((p) => !p.ok && p.method === "File.text"), "Failed open proof missing");
    } catch (err) {
      fails.push(`threw: ${err.message}`);
    }
    return fails;
  });
  assert.deepEqual(failures, []);
}

(async () => {
  const browser = await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  const externalRequests = [];
  page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  page.on("pageerror", (err) => consoleErrors.push(err.message));
  page.on("request", (request) => {
    if (isExternal(request.url())) externalRequests.push(request.url());
  });

  try {
    await waitForBody(page);
    await runChecks(page);
    await page.screenshot({ path: "../notepad_appai/stage1-screenshot.png", fullPage: true });
  } finally {
    await browser.close();
  }

  assert.deepEqual(consoleErrors, []);
  assert.deepEqual(externalRequests, []);
  console.log("✓ Mantle Notepad AppAI: launch/edit/open/save/find/replace/wrap/errors/AppAI gates passed");
  console.log("✓ Phase-1 evidence: no external network requests observed");
  console.log("✓ Screenshot: examples/notepad_appai/stage1-screenshot.png");
})();

import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const BASE = process.env.BASE_URL || "http://localhost:8765";
const PLAYWRIGHT_IMPORT = process.env.PLAYWRIGHT_MODULE_PATH
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE_PATH).href
  : "playwright";
const { chromium } = await import(PLAYWRIGHT_IMPORT);

function isExternal(url) {
  const host = new URL(url).hostname;
  return !["localhost", "127.0.0.1", "::1"].includes(host);
}

async function loadClean(page) {
  await page.goto(`${BASE}/files_appai/?cb=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.evaluate(() => localStorage.removeItem("mantle.files-appai.ledger.v1"));
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => Boolean(window.FilesAppAI), { timeout: 10000 });
}

async function assertions(page) {
  const failures = await page.evaluate(async () => {
    const fail = [];
    const expect = (condition, message) => { if (!condition) fail.push(message); };
    const body = window.FilesAppAI;

    try {
      const declaration = body.readDeclaration();
      const organs = body.readOrganMap();
      const evidence = body.readEvidenceIndex();
      const matrix = body.readStage1Matrix();
      expect(declaration.phase === 1, "declaration is not Phase 1");
      expect(declaration.default_model === "none in Phase 1", "Phase 1 enables a model");
      expect(declaration.network === "disabled", "network is not disabled");
      expect(declaration.source_mutation === "no connected limb", "source mutation limb exists");
      expect(declaration.source_commit === "7aa516aca1a97e08ffd74a5cc79a91d00e828a2c",
        "source commit drifted");
      expect(Object.keys(organs.organs).length === 9, "organ map is incomplete");
      expect(/dormant/i.test(organs.organs.Brain), "Brain is not dormant");
      expect(evidence.kind === "HOST_EVIDENCE_INDEX", "host evidence index missing");
      expect(evidence.local_first_consultation === true, "consultation is not local-first");
      expect(evidence.facts.every((fact) =>
        ["DIRECT", "MEASURED", "STIPULATED", "INFERRED", "UNKNOWN"].includes(fact.evidence)),
        "evidence label was upgraded or lost");
      expect(matrix.length >= 8 && matrix.every((row) => row.status === "PASS"),
        "phenotype gate matrix is not all PASS");
      expect(body.phase1NoModelCalls() === true, "no-model policy failed");
      expect(body.brainStatus().mind === "dormant" && body.brainStatus().mayMutate === false,
        "Brain gained mutation authority");

      expect(body.buildCommand("solution", "Debug", "x64") ===
        "msbuild -restore Files.slnx -p:Configuration=Debug -p:Platform=x64 -v:quiet -clp:ErrorsOnly",
        "solution instinct returned the wrong command");
      expect(body.buildCommand("shared", "Debug", "x64").includes(
        "src/Files.Shared/Files.Shared.csproj"), "shared command targets the wrong project");
      expect(body.classifyPath("src/Files.App/App.xaml.cs") === "main-winui-app",
        "main app path classification failed");
      expect(body.classifyPath("src/Files.App.CsWin32/NativeMethods.txt") === "native-interop",
        "native path classification failed");
      expect(body.classifyPath("tests/Files.App.UITests/test.cs") === "tests",
        "test path classification failed");

      const build = body.ask("How do I build the solution?");
      expect(build.topic === "build" && build.evidence === "DIRECT",
        "build answer did not retain DIRECT evidence");
      expect(build.answer.includes("msbuild -restore Files.slnx"),
        "build answer omitted the verified baseline");
      const unknown = body.ask("What was the maintainer thinking yesterday?");
      expect(unknown.evidence === "UNKNOWN", "unsupported answer was not UNKNOWN");
      expect(body.getLedger().some((entry) =>
        entry.type === "immune_event"
        && entry.detail.kind === "unsupported_claim_contained"),
        "unsupported claim was not contained by Immune");

      const prompt = document.getElementById("assistantPrompt");
      const beforeTyping = body.getLedger().length;
      prompt.focus();
      for (const value of ["b", "bu", "bui", "build"]) {
        prompt.value = value;
        prompt.dispatchEvent(new Event("input", { bubbles: true }));
      }
      expect(body.getLedger().length === beforeTyping, "typing wrote per-keystroke ledger rows");
      prompt.blur();
      await new Promise((resolve) => setTimeout(resolve, 30));
      const commits = body.getLedger().slice(beforeTyping).filter(
        (entry) => entry.type === "HOST_TEXT_COMMIT");
      expect(commits.length === 1
        && commits[0].detail.commit_policy === "submit_or_blur"
        && commits[0].detail.commit_boundary === "assistant_blur",
      "prompt blur did not produce one clean HOST_TEXT_COMMIT");

      document.querySelector('[data-question="Which changes are high risk?"]').click();
      expect(body.getVisibleTranscript().some((message) =>
        message.role === "assistant" && message.text.includes("File operations")),
        "suggested risk question did not produce an evidence answer");

      const gate = document.getElementById("mutationGate");
      gate.click();
      const intent = body.getLedger().findLast((entry) =>
        entry.type === "operator_mutation_intent");
      expect(intent && intent.detail.acknowledged === true
        && intent.detail.capability_granted === false,
      "mutation intent accidentally granted a capability");

      document.querySelector('[data-view="workbench"]').click();
      document.getElementById("buildTarget").value = "app";
      document.getElementById("buildTarget").dispatchEvent(new Event("change", { bubbles: true }));
      expect(document.getElementById("commandOutput").textContent.includes(
        "src/Files.App/Files.App.csproj"), "workbench did not update command output");

      document.getElementById("sourcePath").value = "docs/interop-unmarshaled-conversion.md";
      document.getElementById("classifyPath").click();
      expect(document.getElementById("pathOutput").textContent.startsWith("docs"),
        "path workbench did not expose docs classification");

      expect(document.documentElement.scrollWidth <= window.innerWidth + 1,
        "page has horizontal overflow");
      expect(document.querySelector('img[src="files-logo.png"]').complete,
        "Files visual asset did not load");
    } catch (error) {
      fail.push(`threw: ${error.message}`);
    }
    return fail;
  });
  assert.deepEqual(failures, []);
}

const browser = await chromium.launch(
  process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}
);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const consoleErrors = [];
const externalRequests = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));
page.on("request", (request) => {
  if (isExternal(request.url())) externalRequests.push(request.url());
});

try {
  await loadClean(page);
  await assertions(page);
  await page.click('[data-view="assistant"]');
  await page.screenshot({
    path: "../files_appai/stage1-screenshot.png",
    fullPage: true
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => Boolean(window.FilesAppAI), { timeout: 10000 });
  const mobileOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1
  );
  assert.equal(mobileOverflow, false, "mobile layout has horizontal overflow");
} finally {
  await browser.close();
}

assert.deepEqual(consoleErrors, []);
assert.deepEqual(externalRequests, []);
console.log("Files.AppAI smoke: evidence, instincts, Body boundaries, and responsive UI OK");
console.log("Phase-1 evidence: no external requests observed");

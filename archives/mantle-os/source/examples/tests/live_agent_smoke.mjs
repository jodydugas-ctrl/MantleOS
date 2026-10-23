// Headless mount + runnable Stage-1 gate test for the Mantle live agent.
// Chromium is unavailable in this sandbox (allowlist), so this uses jsdom with
// the SAME React 18.3.1 UMD builds and the SAME Babel presets the page uses.
import { readFileSync } from "fs";
import { JSDOM } from "jsdom";
import Babel from "@babel/standalone";

const html = readFileSync(new URL("../Mantle_Live_Agent.html", import.meta.url), "utf8");
const src = html.match(/<script type="text\/babel"[^>]*>([\s\S]*?)<\/script>/)[1];
const compiled = Babel.transform(src, { presets: ["typescript", "react"], filename: "agent.tsx" }).code;

const dom = new JSDOM(`<!DOCTYPE html><html><body><div id="boot-err" style="display:none"></div><div id="root"></div></body></html>`, {
  url: "http://localhost/",
  runScripts: "outside-only",
  pretendToBeVisual: true,
});
const w = dom.window;
// canvas stub — shard PNG rendering is exercised only on save/export paths;
// give getContext/toBlob inert implementations so incidental calls don't throw
const proto = w.HTMLCanvasElement.prototype;
proto.getContext = () => ({ fillRect(){}, putImageData(){}, getImageData:(x,y,ww,hh)=>({data:new Uint8ClampedArray(ww*hh*4)}), createImageData:(ww,hh)=>({data:new Uint8ClampedArray(ww*hh*4)}), drawImage(){}, fillText(){}, font:"" });
proto.toBlob = (cb) => cb(new w.Blob());
w.fetch = () => Promise.reject(new Error("network disabled in test"));
// jsdom lacks these browser globals; real browsers always have them
import { TextEncoder, TextDecoder } from "util";
w.TextEncoder = TextEncoder; w.TextDecoder = TextDecoder;
w.crypto.subtle || Object.defineProperty(w.crypto, "subtle", { value: (await import("crypto")).webcrypto.subtle });

// load React UMD into the jsdom window
for (const f of ["node_modules/react/umd/react.production.min.js",
                 "node_modules/react-dom/umd/react-dom.production.min.js"]) {
  w.eval(readFileSync(new URL(f, import.meta.url), "utf8"));
}
let failed = null;
w.addEventListener("error", (e) => { failed = e.message; });
try { w.eval(compiled); } catch (e) { console.error("EVAL FAILED:", e.message); process.exit(1); }

// wait for mount + test hook
const t0 = Date.now();
while (Date.now() - t0 < 15000) {
  if (w.document.getElementById("root").firstChild && w.__mantleTest) break;
  await new Promise((r) => setTimeout(r, 100));
}
const root = w.document.getElementById("root");
if (!root.firstChild) { console.error("MOUNT FAILED", failed || "", w.document.getElementById("boot-err").textContent); process.exit(1); }
console.log("MOUNT OK — root has", root.querySelectorAll("*").length, "elements");
if (!w.__mantleTest) { console.error("test hook missing"); process.exit(1); }

// the runnable Stage-1 gate
const report = w.__mantleTest.runSelfAudit();
console.log("SELF-AUDIT:", report.verdict, "—", report.green + "/" + report.total, "rows green");
report.rows.forEach((r) => console.log(" ", r.ok ? "[PASS]" : "[FAIL]", r.id, "·", r.note.slice(0, 80)));
if (report.verdict !== "PASS") process.exit(1);

// organ atlas complete
const organs = Object.keys(w.__mantleTest.organAtlas);
console.log("ORGANS:", organs.length, "-", organs.join(", "));

// schedule + pain behave
const sp = w.__mantleTest.schedulePulse(2, "test wake");
console.log("SCHEDULE:", sp.success ? "OK (due tick " + sp.pulse.dueTick + ")" : "FAILED");
const pain = w.__mantleTest.pain("test interrupt");
console.log("PAIN:", pain.success ? "OK (" + pain.fired + ")" : "FAILED");
// the memory scribe — the exact call shape that failed in the live session
const wr = await w.__mantleTest.appendToShard(w.__mantleTest.state().crystalName, "DISCOVERY_FLAG", "The Grimoire: origin-lore test write");
console.log("APPEND:", wr.ok ? "OK (" + wr.note + ")" : "FAILED: " + wr.error);
if (!wr.ok) process.exit(1);
const st = w.__mantleTest.state();
console.log("STATE: shards=" + Object.keys(st.reservedShards).length,
            "scheduledPulses=" + st.scheduledPulses.length,
            "auditReports=" + st.auditReports.length,
            "gen=" + st.generation);
if (!sp.success || !pain.success) process.exit(1);
console.log("ALL LIVE-AGENT TESTS GREEN");

process.exit(0);

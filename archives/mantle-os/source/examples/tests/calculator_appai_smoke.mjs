import assert from "node:assert/strict";
import vm from "node:vm";
import { readFile } from "node:fs/promises";

class EventStub {
  constructor(type, options = {}) {
    this.type = type;
    this.bubbles = Boolean(options.bubbles);
    this.cancelable = Boolean(options.cancelable);
    this.defaultPrevented = false;
    this.target = null;
  }

  preventDefault() {
    if (this.cancelable) this.defaultPrevented = true;
  }
}

class ElementStub {
  constructor(id = "") {
    this.id = id;
    this.value = "";
    this.textContent = "";
    this.hidden = false;
    this.className = "";
    this.children = [];
    this.listeners = {};
    this.scrollTop = 0;
    this.scrollHeight = 0;
  }

  addEventListener(type, fn) {
    this.listeners[type] ||= [];
    this.listeners[type].push(fn);
  }

  dispatchEvent(event) {
    event.target ||= this;
    for (const fn of this.listeners[event.type] || []) fn(event);
    return !event.defaultPrevented;
  }

  click() {
    this.dispatchEvent(new EventStub("click", { bubbles: true }));
  }

  focus() {
    this.focused = true;
  }

  appendChild(child) {
    this.children.push(child);
    this.scrollHeight = this.children.length;
    return child;
  }
}

function makeDocument(ids) {
  const elements = new Map(ids.map((id) => [id, new ElementStub(id)]));
  elements.get("display").textContent = "0";
  return {
    getElementById(id) {
      return elements.get(id);
    },
    createElement() {
      return new ElementStub();
    }
  };
}

const egg = JSON.parse(await readFile(new URL("../eggs/calculator.json", import.meta.url), "utf8"));
const script = egg.face.source.match(/<script>([\s\S]*)<\/script>/)?.[1];
assert.ok(script, "calculator face has no executable script");

const document = makeDocument([
  "display",
  "keypad",
  "appaiTerminal",
  "appaiLog",
  "appaiForm",
  "appaiPrompt",
  "appaiDot",
  "helpAppAI"
]);
const window = { Event: EventStub };
const context = { window, document, Date, Function, String };

assert.equal(egg.identity.name, "Calculator.AppAI");
assert.ok(egg.controls.find((control) => control.id === "appai"));
assert.ok(egg.controls.find((control) => control.id === "appaiPrompt" && control.commit_policy === "submit_or_blur"));
assert.ok(egg.genome.find((band) => band.band === "appai_terminal"));

vm.runInNewContext(script, context);
assert.ok(window.CalculatorAppAI, "calculator face did not expose test API");

document.getElementById("helpAppAI").click();
assert.equal(window.CalculatorAppAI.isTerminalOpen(), true, "AppAI terminal did not open");
assert.equal(
  window.CalculatorAppAI.getVcwEntries().filter((entry) => entry.type === "terminal_opened").length,
  1,
  "terminal opener did not record one bounded event"
);

const prompt = document.getElementById("appaiPrompt");
const beforeTyping = window.CalculatorAppAI.getVcwEntries().length;
prompt.value = "h";
prompt.dispatchEvent(new EventStub("input", { bubbles: true }));
prompt.value = "he";
prompt.dispatchEvent(new EventStub("input", { bubbles: true }));
prompt.value = "help";
prompt.dispatchEvent(new EventStub("input", { bubbles: true }));
assert.equal(
  window.CalculatorAppAI.getVcwEntries().length,
  beforeTyping,
  "prompt input wrote per-keystroke VCW entries"
);

prompt.dispatchEvent(new EventStub("blur", { bubbles: true }));
let commits = window.CalculatorAppAI.getVcwEntries().filter((entry) => entry.type === "textbox_committed");
assert.equal(commits.length, 1, "blur did not produce exactly one text-field commit");
assert.equal(commits[0].detail.reason, "blur");
assert.equal(commits[0].detail.chars, 4);

prompt.value = "what is on the display?";
document.getElementById("appaiForm").dispatchEvent(
  new EventStub("submit", { bubbles: true, cancelable: true })
);
commits = window.CalculatorAppAI.getVcwEntries().filter((entry) => entry.type === "textbox_committed");
assert.equal(commits.length, 2, "submit did not produce exactly one additional text-field commit");
assert.equal(commits[1].detail.reason, "submitted");
assert.equal(prompt.value, "", "submitted prompt was not cleared");
assert.equal(
  window.CalculatorAppAI.getVcwEntries().filter((entry) => entry.type === "mind_message").length,
  2,
  "terminal did not record bounded user/MIND transcript markers"
);
assert.equal(
  window.CalculatorAppAI.getVcwEntries().some((entry) => entry.type === "keypress" || entry.type === "prompt_input"),
  false,
  "terminal stored keypress-style prompt entries"
);

console.log("Calculator.AppAI smoke: AppAI terminal and submit/blur text commits OK");

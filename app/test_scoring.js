"use strict";

const assert = require("node:assert/strict");
const model = require("./modele.json");
const { scoreClient } = require("./scoring.js");

assert.equal(model.check.length, 3, "expected three notebook check clients");
for (const [index, sample] of model.check.entries()) {
  const actual = scoreClient(model, sample.input).pd;
  assert.ok(
    Math.abs(actual - sample.pd) <= 1e-6,
    `check client ${index + 1}: expected ${sample.pd}, got ${actual}`
  );
}

console.log("OK: les 3 PD correspondent aux valeurs du notebook (tolérance 1e-6).");

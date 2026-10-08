"use strict";

function normalizeClient(model, input) {
  const normalized = { ...input };
  const clamped = {};

  for (const name of model.numeric_inputs) {
    if (name === "loan_to_income") continue;
    const value = Number(input[name]);
    const range = model.ranges[name];
    if (!Number.isFinite(value) || !range) {
      throw new Error("Valeur numérique manquante ou invalide : " + name);
    }
    normalized[name] = Math.max(range.p1, Math.min(range.p99, value));
    if (normalized[name] !== value) clamped[name] = { from: value, to: normalized[name] };
  }

  if (normalized.annual_inc <= 0) {
    throw new Error("Le revenu annuel doit être supérieur à zéro.");
  }
  for (const [name, levels] of Object.entries(model.categories)) {
    if (!levels.includes(input[name])) {
      throw new Error("Catégorie invalide : " + name);
    }
  }

  normalized.loan_to_income = normalized.loan_amnt / normalized.annual_inc;
  return { input: normalized, clamped };
}

function scoreClient(model, input) {
  const normalized = normalizeClient(model, input);
  const contributions = {};
  let logit = model.intercept;

  for (let i = 0; i < model.features.length; i += 1) {
    const feature = model.features[i];
    let value;
    if (feature === "loan_to_income") {
      value = normalized.input.loan_to_income;
    } else if (model.numeric_inputs.includes(feature)) {
      value = normalized.input[feature];
    } else {
      const category = Object.keys(model.categories).find((name) =>
        feature.startsWith(name + "_")
      );
      if (!category) throw new Error("Caractéristique inconnue : " + feature);
      const level = feature.slice(category.length + 1);
      value = normalized.input[category] === level ? 1 : 0;
    }

    const z = (value - model.mean[i]) / model.scale[i];
    const contribution = model.coef[i] * z;
    logit += contribution;

    const category = Object.keys(model.categories).find((name) =>
      feature.startsWith(name + "_")
    );
    const variable = category || feature;
    contributions[variable] = (contributions[variable] || 0) + contribution;
  }

  return {
    ...normalized,
    logit,
    pd: 1 / (1 + Math.exp(-logit)),
    contributions,
  };
}

const api = { normalizeClient, scoreClient };
if (typeof module !== "undefined" && module.exports) module.exports = api;
if (typeof window !== "undefined") window.TrafficLightScoring = api;

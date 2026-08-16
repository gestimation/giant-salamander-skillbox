# samplesize200 Quick Guide

## samplesize200 — Chat with 200+ solutions to size your study

samplesize200 is a Giant Salamander Skillbox skill that organizes study plans through conversation, selects a registered method, and calculates the required study size. It contains 188 calculators and 105 research examples, for a total of 293 solutions. When information is missing, it asks only for the items required for the calculation.

## Installation

The official distribution source is [GitHub Releases](https://github.com/gestimation/giant-salamander-skillbox/releases). For a first installation, use the all-in-one plugin `giant-salamander-skillbox-1.0.0.zip`, which contains `readatable`, `reviewcitation`, `samplesize200`, and `draftcostsheet`. Install the ZIP unchanged from the plugin screen in ChatGPT Work, Codex, or Claude Code; do not extract or repackage it.

To install only samplesize200, install the single-skill plugin `samplesize200-1.0.0-rc.9.zip` in ChatGPT Work or Codex. Do not install both the all-in-one plugin and the single-skill plugin.

For Codex marketplace installation, run:

```text
codex plugin marketplace add gestimation/giant-salamander-skillbox
codex plugin add giant-salamander-skillbox@giant-salamander-skillbox
```

For Claude Code Desktop marketplace installation, enter these slash commands in the chat input:

```text
/plugin marketplace add gestimation/giant-salamander-skillbox
/plugin install giant-salamander-skillbox@giant-salamander-skillbox
/reload-plugins
```

The skill's machine name and display name are both `samplesize200`.

## Try it

Describe what you want to know in ordinary language.

> Calculate the sample size required to detect a correlation coefficient of 0.5.

> Plan a 2 x 2 crossover bioequivalence study with GMR 0.90, CV 30%, and limits 0.80 to 1.25.

> Measurements are taken at years 0, 1, and 3, with 100 participants per group, correlation 0.4, and 80% power. Calculate the detectable annual slope difference.

You do not need to choose the method yourself. samplesize200 never substitutes a nearby formula for an unsupported method.

## Standard defaults

The following defaults are used only when conditions are omitted for an ordinary superiority study.

| Condition | Default |
|---|---|
| Significance level | 5% |
| Target power | Three scenarios: 80%, 90%, and 95% |
| Clearly directional one-group hypothesis | One-sided |
| Ordinary two-group superiority comparison | Two-sided |
| Ordinary two-group sample-size design | 1:1 allocation |

These defaults are not applied automatically to noninferiority, equivalence, multiplicity-adjusted, confidence-interval precision, or Bayesian designs. samplesize200 asks about conditions that can change the conclusion, including margins, equivalence limits, precision targets, event rates, variances, correlations, and attrition rates.

## Main coverage

- Means, proportions, incidence rates, and survival outcomes for one, two, or three or more groups
- Correlation, inter-rater agreement, diagnostic accuracy, and reference intervals
- Noninferiority, equivalence, and bioequivalence
- Repeated measures, ordinal outcomes, competing risks, and cluster-randomized trials
- Required sample size, required number of events, and required participants per cluster when the number of clusters is fixed
- Achieved power and detectable effect for supported calculators
- Attrition-adjusted sample size
- Comparison with research examples and review of calculation conditions

samplesize200 asks for clarification when the calculation depends on whether a number is total or per group, the direction of an allocation ratio, the direction of a hypothesis, or a similar distinction.

## Four modes

You normally do not need to specify a mode. When useful, request one of the following roles.

| Mode | Purpose |
|---|---|
| `CALCULATE` | Ask only for required conditions and perform the calculation |
| `STATISTICIAN` | Compare methods, assumptions, and sensitivity analyses |
| `TEACHER` | Explain the calculation method and research examples |
| `REVIEWER` | Check calculations reported in a protocol or article |

## Reading the result

The result shows the adopted values, important assumptions, and the final sample size or number of events. Group- or sequence-specific allocations are shown when needed. If attrition was not specified, the result is not adjusted for attrition.

After a calculation, ask to see an example to retrieve one research example using the same or a related method. Values from a research example are never silently reused as unspecified conditions for the current calculation.

## Quality and sources

samplesize200 uses the bundled, validated samplesize200 Alpha 0.6.9 engine. The primary source for its calculation methods is: Machin D, Campbell MJ, Tan SB, Tan SH. Sample size tables for clinical studies. 3rd ed. Chichester (UK): Wiley-Blackwell; 2009. doi:10.1002/9781444300710. Book chapter and example numbers are not embedded in identifiers; they are retained as traceability metadata.

The original components of this skill are provided under the MIT License. Copyright (c) 2026 Shiro Tanaka. Third-party software remains subject to its respective license.

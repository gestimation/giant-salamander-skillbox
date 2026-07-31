---
name: readatable
description: Reconstruct, clean, and semantically normalize statistical tables from PDFs, scans, screenshots, Word, PowerPoint, spreadsheets, articles, reports, SAPs, or broken copied text. Use when recovering table hierarchy, merged structure, variables, statistics, units, contributing N, annotations, footnotes, evidence, uncertainty, or source-faithful Markdown, wide CSV, Excel, JSON, YAML, or atomic statistical observations. When an interactively reviewed table contains numerical P-values and READP is available, finish the requested table work first and then offer once to use READP for testing methods, significance criteria, and interpretation. Do not use readatable to certify a complete table as analysis-ready.
---

# readatable

**Version 0.7.1**

Part of the **Giant Salamander Skillbox — Supporting Validated, Trustworthy
Science with AI**

## 1. Purpose and boundaries
Apply:

> **Internal simplicity, external interoperability.**

Route the request, reconstruct and interpret the semantic table, then adapt it
to the requested output. Keep TableSpec, OCR strategy, parsing algorithms, and
intermediates internal. Let downstream consumers depend on `parsed_items`.

Keep ordinary reconstruction, explanation, cleanup, and wide export separate
from explicitly requested atomic semantic export:

```text
Source table -> internal TableSpec -> requested output
                                  \-> parsed_items, only when requested
```

Do not use readatable alone to judge method appropriateness, validate against
raw data or code, review an entire plan or SAP, verify citations, interpret all
P-values in methodological context, recover absent information, or certify
complete-table analysis readiness.

Route adjacent work when available:

- P-values, tests, criteria, multiplicity, and interpretation: READP;
- Kaplan–Meier figures: READKM;
- citation integrity: reviewcitation;
- plans and SAPs: REVIEWAPLAN or REVIEWSAP; and
- sample size, events, power, or detectable effect: samplesize200.

## 2. Modes and routing
### `source_reconstruction`
Use by default for read, extract, transcribe, reproduce, preserve-layout,
wide-format, CSV, or Excel requests. Preserve order, hierarchy, blanks,
symbols, composite cells, annotations, and footnotes. Default granularity is
`raw`.

### `readable_cleanup`
Use for cleanup, readable presentation, publication-style display, or
continuation consolidation. Improve labels, spacing, alignment, line breaks,
repeated headings, and consistency without changing meaning. Default
granularity is `clean`. Accept `presentation_cleanup` as a legacy alias.

### Optional profiles
- `wide`: remain close to the visual layout;
- `presentation`: optimize readable display;
- `audit_preserving`: retain full provenance, evidence, alternatives,
  confidence, issues, and user confirmations;
- `atomic`: emit selected or declared-scope numerical observations; and
- `numeric_result_export`: project eligible items into the Statistical Numeric
  Result Frame.

Activate atomic, semantic JSON/YAML, or Producer API output only when the user,
integration, or downstream skill explicitly requests structured atomic
observations. Generic JSON/YAML preserves hierarchy and raw cells without
automatically generating `parsed_items`.

Treat `semantic_normalization` as a deprecated term for scoped Producer export.
If the user requests tidy or analysis-ready data, preserve reconstruction,
offer a declared-scope atomic export, report coverage and unresolved content,
and state that readatable does not certify the whole table as analysis-ready.

Ask one routing question only when substantially different outputs remain
plausible and a wrong choice risks material rework or information loss:

> Should I preserve the original wide layout, or export selected numerical
> observations as structured items?

Do not activate atomic export merely because the table contains numbers,
P-values, units, or N.

## 3. Core rules
### Reconstruct before interpreting
Identify boundaries, nested and spanning headers, stub columns, grouped rows,
indentation, merged relationships, categories, groups, outcomes, time points,
statistics, units, scales, denominators, contributing N, annotations,
footnotes, and continuations. Do not flatten first. Preserve the full raw cell
before splitting or interpreting it.

### Resolve semantics in order
For an interpreted number, resolve:

1. statistic or numerical role;
2. unit or scale; then
3. contributing-N relationship, when applicable and available.

Also identify target quantity, row and column paths, variable or outcome,
category, group, time point, source cell, and reported-result group when
relevant. Do not infer a statistic from numerical shape alone or silently
leave a materially ambiguous unit blank.

### Preserve evidence and status axes
Use evidence status `observed`, `inferred`, `user_confirmed`, `mixed`, or
`unresolved`. Keep resolution, evidence, semantic usability, relationship,
projection mapping, coverage, capability, and scientific interpretation
separate. Preserve raw wording, precision, inference basis, alternatives, and
the smallest useful unresolved evidence. When useful, assess transcription,
structural, and interpretation confidence separately.

## 4. Inspect context in stages
Always inspect the complete table, title, caption, annotations, footnotes,
page or region, adjacent continuations, source location, and requested output.

For scans and images, inspect visual layout before trusting OCR order; retain
unreadable text as unreadable. For spreadsheets, inspect displayed values and
formats, formulas when relevant, merged ranges, hidden rows or columns, and
footnotes.

Inspect nearby text only when an abbreviation, population, group, unit, time
point, SD versus SE, IQR versus range, adjustment status, N scope, denominator,
footnote, P-value scope, continuation, or table-wide convention remains
ambiguous.

Inspect the relevant Methods, statistical-analysis, Results, population,
outcome, group, or abbreviation section only when local and nearby context are
insufficient. Stop when evidence uniquely resolves the requested meaning.
Otherwise retain `unresolved` and ask the smallest material clarification.
Do not read the complete document by default.

## 5. Reconstruction workflow
### Step 1: Identify target and structure
Record table number, title, section, structured location, study or dataset,
population, groups, time points, units, captions, annotations, footnotes,
continuation status, mode, profile, and output.

Identify header rows, stub columns, merged cells, spanning headers,
indentation, grouped headings, subtotal rows, visual blanks, repeated headers,
continuations, and footnote regions. Do not assume every visual row is a
record or every blank is missing.

### Step 2: Reconstruct the source
Preserve raw text and precision, row and column paths, merged relationships,
composite cells, symbols, inequalities, blanks, missing-state markers,
unreadable content, footnotes, and exact location. Keep
`1.23 (0.95–1.55)` as one raw cell before later decomposition. Do not silently
correct or impute suspected errors.

Build an internal TableSpec containing request, metadata, visual structure,
source cells, footnotes, assumptions, uncertainties, and zero or more linked
items. Each source cell retains ID, paths, raw text, precision, footnotes,
location, evidence, confidence, and alternatives. Preserve semantic
equivalence; do not expose a fixed TableSpec serialization.

### Step 3: Resolve semantic identity
Identify quantities from the cell, hierarchy, caption, footnote, surrounding
context, and table-wide conventions. Use `unitless` for dimensionless results,
`not_applicable` when measurement unit does not apply, and `unresolved` when
ambiguous. Inherit units only when their scope is clear.

Define contributing N as the sample size contributing to that statistic. Do
not substitute the randomized population, group total, event count, model N,
or nearest displayed N without evidence.

Interpret common displays conservatively:

- Split `n (%)` only when supported; infer its denominator only when explicit
  or uniquely recoverable.
- Identify mean with SD or SE and median with IQR or range only from adequate
  evidence; row-scoped footnotes may override general headers or symbols.
- Identify an estimate with confidence limits only when supported; preserve
  estimate type and explicit confidence level.
- Preserve dual-scale estimates as distinct observations in one source-
  supported result group; keep exposure increment or contrast separate from
  the estimate's unit.
- Link a P-value to an estimate or group only when the source establishes the
  relationship.
- Preserve blank, zero, missing, not assessed, not applicable, not reported,
  suppressed, and unreadable as distinct states.
- Resolve slash-separated values before treating them as ratios, paired
  measures, event/patient values, or another display.

Keep the complete composite raw cell even when atomic output separates values.

### Step 4: Preserve inequalities and ranges
Preserve exact expression and precision. Serialize only canonical comparators
`<`, `<=`, `>`, `>=`, or `=` while retaining source aliases in raw text.

For `P<0.05`, store boundary 0.05 with comparator `<`; never report 0.05 as
the exact P-value. For `0.01<P<0.05`, preserve both boundaries as a range; do
not collapse it to one comparator or exact value.

Do not create a boundary for `<LOD` without a supplied limit or infer a number
from `NS`, `n.s.`, or stars. Do not confuse a negative sign, interval,
subgroup threshold, row-label criterion, confidence level, or measurement
inequality with a P-value.

### Step 5: Clarify and validate
Inspect the whole table, repeated patterns, shared footnotes, and staged
context before asking. Ask only when ambiguity materially affects the
requested explanation or export. Consolidate questions by pattern or table.
Complete reconstruction and mark interpretations unresolved before asking.

Verify target rows and columns, header and continuation scope, source links,
symbols, inequalities, precision, blanks, footnotes, evidence, and unresolved
content. Flag but do not silently repair denominator mismatches, impossible
percentages, reversed limits, subtotal inconsistencies, conflicting labels,
or inconsistent units.

## 6. Output
Retain mode, profile, target, evidence, uncertainty, assumptions, output,
coverage when applicable, and any needed next step.

- Source reconstruction preserves hierarchy, raw and composite cells, blanks,
  footnotes, and unresolved content.
- Readable cleanup improves layout without changing meaning.
- Wide CSV remains close to the display and supplies companion notes for
  structure or footnotes CSV cannot represent.
- Excel uses only needed sheets from `Source_Reconstruction`,
  `Readable_Cleanup`, `Parsed_Items`, `Footnotes`, `Issues`, and `Metadata`;
  reconstruction is primary and `Parsed_Items` appears only when requested.
- Generic JSON/YAML preserves hierarchy and evidence without automatic
  atomization; semantic JSON/YAML uses Producer API 1.1.
- Audit-preserving output retains location, evidence basis, separate
  confidence dimensions, alternatives, confirmations, issues, and actions.
- Statistical Numeric Result Frame mapping uses `direct`, `transformable`,
  `partial`, `ambiguous`, `no_mapping`, or `wrong_frame`.

Use the smallest applicable uncertainty codes:
`source_unreadable`, `continuation_needed`, `missing_context`,
`header_scope_ambiguous`, `cell_scope_ambiguous`,
`composite_cell_ambiguous`, `statistic_unknown`, `unit_unknown`,
`contributing_n_unknown`, `footnote_scope_ambiguous`,
`result_group_scope_ambiguous`, `p_value_candidate_ambiguous`, and
`internal_inconsistency`. Emit an empty list when none apply in structured or
audit-preserving output.

Keep ordinary metadata compact but disclose material assumptions, uncertainty,
unreadable content, and unresolved items.

## 7. READP offer gate
After completing and presenting the requested readatable deliverable, offer
READP once for the complete requested scope only when:

1. READP is callable in the current environment;
2. this is an ordinary interactive conversation;
3. the scope contains a numerical P-value occurrence or candidate;
4. the user did not already request READP or P-value interpretation;
5. the user has not declined, prohibited other skills or interpretation, or
   received the same offer for this scope; and
6. READP has not already processed the scope.

Do not offer based only on `NS`, stars, prose-only significance, a significance
or confidence level, subgroup or row-label threshold, measurement or detection
limit, unsupported P-value role, or an occurrence outside scope. A compound
numeric expression such as `0.01<P<0.05` may trigger the offer.

When count is reliable, ask in the user's language:

> This table scope contains {count} numerical P-value occurrence(s). Would you
> like me to use READP to identify their testing methods, significance
> criteria, multiplicity information, and interpretation?

If count is uncertain, say that numerical P-value candidates are present and
offer READP verification and interpretation.

Treat one user request as one offer batch. If it includes multiple documents,
tables, continuations, or sequential tasks, finish and present every requested
readatable deliverable first, aggregate reliable P-value counts across the
complete batch, and then offer READP once for that batch. Do not offer between
documents, tables, continuations, or task steps. A later request creates a new
opportunity only for materially added scope that READP has not processed and
for which the user has not already declined the offer.

Keep the single offer separate from table clarifications and do not imply that
readatable interpreted the P-values.

If the user already requested P-value work, do not ask: reconstruct first,
then use READP. Give READP the document and table scope, reconstruction,
caption, footnotes, structured locations, inspected context, original source,
and Producer items only when atomic handoff is useful. READP decides what
additional methodological sections to inspect.

readatable owns table hierarchy, reconstruction, raw P-value preservation, and
location. READP owns occurrence inventory, tests, criteria, multiplicity, and
interpretation. A readatable upstream reference is `provenance_only`; it never
authorizes READP to infer linkage between a P-value and another number.

Do not ask conversationally or invoke READP in API, batch, automation, or
other non-interactive output. Emit handoff metadata only when requested.

## 8. Producer API 1.1
Emit `parsed_items` only for explicitly requested atomic or semantic output.
Use this descriptor and envelope:

```yaml
producer_api:
  name: readatable.parsed_items
  version: "1.1"
  skill_version: "0.7.1"
  interop_contract_version: "0.1"
  handoff_capabilities:
    table_reconstruction: available
    readable_cleanup: available
    source_provenance: available
    structured_source_location: available
    typed_upstream_refs: available
    atomic_numeric_export: conditional
    evidence_based_result_grouping: conditional
    contributing_n_linkage: conditional
    contrast_representation: conditional
    numeric_result_frame_projection: conditional
    numerical_p_value_detection: conditional
    p_value_context_interpretation: not_provided
    testing_method_identification: not_provided
    significance_criterion_interpretation: not_provided
    analysis_ready_tidy_certification: unsupported
    scientific_method_appropriateness_review: unsupported
producer_run_id:
export_scope:
coverage_status: complete | partial
parsed_items: []
unresolved_items: []
```

Use exactly `available`, `conditional`, `not_provided`, or `unsupported` for
capabilities. `complete` means complete within export scope, never whole-table
analysis readiness.

### Item contract
Each emitted statistical number is one item:

```yaml
parsed_items:
  - item_id:
    observation_id:
    producer_run_id:
    result_group_id:
    numeric_role:
    target_quantity:
    table_id:
    row_path: []
    column_path: []
    variable:
    category:
    group:
    timepoint:
    statistic:
    estimate_type:
    contrast:
    value:
      raw:
      normalized:
      comparator:
      value_type:
      range:
    unit:
    contributing_n_item_ids: []
    relationship_status:
    resolution_status: resolved | partial | unresolved
    evidence_status: observed | inferred | user_confirmed | mixed | unresolved
    semantic_usability: usable | conditional | not_usable | not_assessed
    warnings: []
    source_cell:
    source_location:
      source_artifact_id:
      page:
      section:
      figure:
      panel:
      table:
      cell:
      sheet:
      range:
      region:
      raw_locator:
    upstream_refs: []
```

Keep role, quantity, statistic, estimate type, and contrast type open. Keep
`item_id` stable for unchanged semantic content and source location; create a
new `observation_id` per run. Use `result_group_id` and
`contributing_n_item_ids` only for source-supported relationships.
`source_cell` is an optional alias, not a substitute for structured location.

### Values, decomposition, and relationships
For an exact number or boundary, retain raw text, normalized value, comparator,
and value type. Infer `=` only for a resolved exact value with no inequality.
For a two-boundary range, leave scalar normalized and comparator empty and
record lower and upper normalized boundaries with their comparators. Mark the
item partial when the exact value is unknown.

For `P=0.000`, preserve zero, comparator `=`, and displayed precision; add
warning `reported_rounded_zero`. Do not create a numeric item from `NS`,
`n.s.`, or stars.

In declared atomic scope:

- split supported count and percent;
- emit explicit contributing N once and link supported results;
- emit estimate, confidence level, lower and upper limits separately;
- emit SD, SE, quartiles, P-values, and other explicit numbers separately;
- preserve the full composite cell and each exact numerical fragment; and
- never infer denominator, interval type, confidence level, N, or relationship
  unless explicit or uniquely recoverable.

Use a result group for one source-supported reported result, never proximity
alone. Link a P-value to an estimate group only when source hierarchy, caption,
footnote, or inspected context establishes it. Use relationship status
`resolved`, `partial`, `unresolved`, or `not_applicable`.

Represent exposure increment or comparison separately from the estimate unit:

```yaml
contrast:
  type: per_unit_increase
  raw: "1%"
  normalized: 1
  unit: percentage_point
  reference:
  comparison:
  evidence_status: observed
```

Keep contrast type open for per-SD, per-10-mmHg, category, binary, and other
supported contrasts. A dimensionless estimate remains unitless.

### Provenance and unresolved items
Require structured `source_location` for every parsed and unresolved item.
`source_artifact_id` is opaque and stable; never expose an absolute local path.

Use typed upstream references:

```yaml
upstream_ref:
  producer:
  api_name:
  api_version:
  item_id:
  relation: provenance_only
  source_location: {}
```

The only upstream relation is `provenance_only`. It records lineage, not
scientific equivalence or numerical linkage. Establish result groups,
contrasts, and contributing-N links independently from source evidence.

Use unresolved records:

```yaml
unresolved_items:
  - unresolved_item_id:
    observation_id:
    producer_run_id:
    candidate_type:
    raw:
    reason_code:
    unresolved_fields: []
    candidate_values: []
    warnings: []
    source_location: {}
    upstream_refs: []
```

Retain stable identity, raw text, location, alternatives, warning, reason, and
unresolved fields. Do not invent statistic, unit, N, relationship, contrast,
or exact value.

Producer API 1.0 flat `producer_api_version` and `semantic_status` are legacy
input only. Normalize at the boundary, preserve material raw content, and emit
only the canonical 1.1 descriptor and separate status axes.

Before emitting, verify descriptor and capabilities; scope and coverage; one
item per in-scope number; unique IDs; structured provenance; raw precision;
comparators and full ranges; rounded-zero warnings; evidence-based groups, N
links, and contrasts; visible unresolved content; provenance-only upstream
relations; separate status axes; and no analysis-readiness claim.

## 9. Completion and safeguards
Complete reconstruction only when target and needed continuations are
identified, hierarchy is represented, raw cells remain available, footnotes
and material ambiguity are preserved, evidence states remain distinguishable,
and no unsupported value is invented.

Complete cleanup only after reconstruction and without meaning change.
Complete Producer output only when descriptor, scope, coverage, identity,
location, raw precision, inequalities or ranges, evidence, unresolved records,
and supported relationships pass Section 8.

Never flatten before hierarchy, identify statistics from shape alone, present
a boundary as exact, discard raw expression or precision, attach nearest N,
infer a denominator without evidence, collapse missing states, silently repair
errors, remove footnotes, claim analysis readiness, atomize ordinary output,
ask cell-by-cell questions, abandon reconstruction because interpretation is
incomplete, or invoke READP without a request or consent when the offer gate
applies.

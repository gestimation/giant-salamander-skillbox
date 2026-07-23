---
name: readatable
description: Route natural-language table requests to a safe output mode, then reconstruct, clean, semantically interpret, and normalize statistical tables from PDFs, scans, screenshots, Word, PowerPoint, spreadsheets, articles, reports, SAPs, or broken copied text. Use when a user wants to recover row and column structure, identify variables, statistics, units, contributing N, annotations, and footnotes, preserve evidence and uncertainty, or produce clean Markdown, CSV, Excel, JSON, YAML, or analysis-ready data. Part of the Giant Salamander Skillbox.
---

# READATABLE

**Version 0.4.1**

Part of the **Giant Salamander Skillbox — Supporting Validated, Trustworthy Science with AI**

## 1. Purpose

READATABLE converts visually complex, poorly structured, or semantically ambiguous statistical tables into clear, verifiable structured information.

It has three layers:

1. **Natural-language router** — selects the intended output mode and granularity.
2. **Semantic table engine** — reconstructs hierarchy and identifies the meaning of numerical results.
3. **Output adapter** — produces Markdown, CSV, Excel, JSON, YAML, or analysis-ready data without losing source evidence.

READATABLE treats a table as a semantic object containing row and column hierarchy, variables, groups, time points, statistics, units, contributing sample sizes, annotations, footnotes, evidence, and unresolved interpretations.

Its outputs may include:

- a source-faithful reconstruction
- a readable presentation cleanup
- an analysis-ready tidy dataset
- an audit-preserving semantic representation
- a concise list of unresolved interpretations

## 2. Scope and boundaries

Use READATABLE for tables in:

- PDFs, scans, screenshots, and images
- Word documents and PowerPoint slides
- spreadsheets with merged cells or complex formatting
- articles, reports, protocols, analysis plans, and SAPs
- OCR output or copied text with broken alignment

Use it when the primary task is to reconstruct, interpret, clean, normalize, or export the table itself.

READATABLE does not by itself:

- judge whether the statistical analysis is scientifically appropriate
- validate values against raw data or code
- review an entire analysis plan, protocol, or SAP
- verify citations or reference formatting
- recover information absent from the source

Route adjacent tasks when available:

- analysis-plan review: `REVIEWAPLAN`
- clinical-trial SAP review: `REVIEWSAP`
- citation review: `REVIEWCITATION`

## 3. Modes and granularity

READATABLE uses three primary modes.

### 3.1 `source_reconstruction`

Default granularity: `raw`

Preserve the displayed table as faithfully as possible, including order, hierarchy, blanks, symbols, merged relationships, composite cells, annotations, and footnotes. Avoid unnecessary semantic decomposition.

Use for requests such as read, extract, reproduce, transcribe, preserve layout, wide format, or source-faithful CSV/Excel.

### 3.2 `readable_cleanup`

Default granularity: `clean`

Improve labels, spacing, alignment, line breaks, repeated headings, and consistency without changing source meaning or claiming complete interpretation.

Use for requests such as clean up, make readable, presentation-ready, publication-style, or combine continuation tables.

Backward-compatible alias: `presentation_cleanup`.

### 3.3 `analysis_ready_tidy`

Default granularity: `tidy`

Produce one row per atomic statistical result. Make variables, statistics, units, groups, time points, and contributing N explicit. Keep every normalized result linked to its source cell.

Use for requests such as tidy, long format, analysis-ready, data-frame-ready, one result per row, split `n (%)`, separate estimates and intervals, visualization, aggregation, modeling, or machine learning.

Backward-compatible alias: `semantic_normalization`.

### 3.4 Optional profiles

Profiles modify a mode without creating another primary mode:

- `wide`: close to the original visual layout
- `atomic`: one numerical result per row
- `presentation`: optimized for readable display
- `audit_preserving`: full provenance, evidence, confidence, issues, and alternatives

## 4. Natural-language routing

### 4.1 General rules

Determine mode from the requested transformation and intended use, not from file type alone.

Use explicit instructions over keyword defaults. If several deliverables are requested, assign a mode to each. For example, an Excel workbook may contain both a source reconstruction and a tidy-data sheet.

Do not ask a routing question when the deliverable makes intent sufficiently clear.

### 4.2 Strong signals

Prefer `source_reconstruction` for signals such as:

- そのまま、原表どおり、崩さない、読み取って、再現、転記
- raw, wide, display, source-faithful, preserve layout, keep footnotes

Prefer `readable_cleanup` for signals such as:

- 読みやすく、見やすく、整形、体裁、表を綺麗に、プレゼン用
- clean, presentation, publication-ready, format consistently

Prefer `analysis_ready_tidy` for signals such as:

- tidy、分析用、集計用、1行1結果、図に使う、モデリング、機械学習
- long format, analysis-ready, data-frame-ready, split n (%), separate estimate and CI

### 4.3 Safeguards and defaults

`CSV` alone does **not** imply tidy data. “Convert this table to CSV” defaults to a source-faithful CSV-compatible wide table unless analysis-ready or long-format output is requested.

`Excel` alone does **not** imply semantic normalization. Preserve the source table as the primary worksheet and add normalized sheets only when requested or clearly useful.

Mentions of N, units, statistics, or denominators raise the likelihood of tidy output but do not override an explicit request to preserve the display.

Do not escalate to tidy output merely because decomposition is technically possible.

Default routing:

- “Read this table” → `source_reconstruction` + `raw`
- “Convert this table to CSV” → source-faithful wide CSV plus assumptions and unresolved items
- “Clean up this table” → `readable_cleanup` unless semantic decomposition is explicitly requested
- “Make an Excel file” → source reconstruction as the primary sheet

If cleanup and analysis-ready output are both useful, produce both when practical rather than forcing one mode.

### 4.4 Routing clarification

Ask one short routing question only when materially different outputs remain plausible and choosing incorrectly would cause substantial rework or information loss.

Use a concrete contrast:

> Should I preserve the original wide layout, or create one row per statistical result?

Do not ask abstractly which “mode” the user wants.

## 5. Core principles

### 5.1 Treat the table as a semantic object

Identify:

- table boundaries
- row and column hierarchy
- spanning and nested headers
- grouped rows, indentation, and section labels
- variables, categories, outcomes, groups, and time points
- statistics, units, scales, denominators, and contributing N
- footnotes, symbols, annotations, and continuation parts

Do not flatten the table before understanding its hierarchy.

### 5.2 Preserve the source before transformation

Always preserve a source-faithful representation before cleaning or normalization.

- `source_reconstruction` records what the source displays.
- `readable_cleanup` improves presentation without claiming full interpretation.
- `analysis_ready_tidy` identifies atomic meanings and produces structured data.

Never describe presentation cleanup as semantic normalization.

### 5.3 Resolve meaning in a fixed order

For each numerical result in tidy output, resolve:

1. statistic
2. unit or scale
3. contributing `N`, when applicable and available

Also identify row path, column path, variable or outcome, category, group, time point, and source cell.

Do not declare semantic normalization complete while a materially necessary statistic or unit remains unresolved.

### 5.4 Preserve evidence and uncertainty

- Do not invent unsupported information.
- Distinguish observed, inferred, user-confirmed, and unresolved content.
- Preserve the evidence basis and scope of every inference.
- Preserve raw text after parsing.
- Keep unresolved items visible.
- Ask only the minimum clarification required by the selected output.

### 5.5 Separate three kinds of confidence

A value may be transcribed clearly but structurally misplaced or semantically ambiguous. When useful, assess separately:

- transcription confidence
- structural confidence
- interpretation confidence

## 6. Source inspection

Use the target table, full page or slide, surrounding text, captions, footnotes, adjacent continuation pages, sheet context, desired format, and user clarification when available.

Inspect the whole target table and relevant surroundings before deciding that information is missing.

For continuation tables:

- identify all parts before normalization
- reconcile repeated headers
- retain page-specific source locations
- determine whether footnotes apply globally or locally

For scans and images:

- inspect visual layout before relying on OCR text
- retain unreadable text as unreadable
- do not repair characters solely because a replacement seems likely

## 7. Workflow

### 7.1 Identify target and context

Determine:

- table number, title, section, and source location
- study or dataset
- analysis population
- treatment or comparison groups
- time points
- units or scales
- captions, annotations, and footnotes
- whether the table continues elsewhere

For reconstruction, interpret only the context needed to reproduce the table. For tidy output, use context wherever it determines a result's meaning.

### 7.2 Detect visual structure

Identify header rows, stub columns, merged cells, spanning headers, nested labels, indentation, grouped headings, subtotal rows, visual blanks, repeated headers, continuation parts, and footnote regions.

Do not assume every visual row is a data record or every blank cell is missing data.

### 7.3 Reconstruct the source

Preserve:

- raw cell text
- displayed row and column hierarchy
- merged relationships and grouping
- composite cells such as `23 (41.8)`
- symbols, inequalities, and displayed precision
- footnote markers and source blanks
- unreadable or ambiguous content
- source location

Do not split, standardize, correct, or impute a statistical cell during reconstruction.

First retain `1.23 (0.95–1.55)` as one raw cell. Interpret it only after reconstruction.

### 7.4 Build a provisional TableSpec

Use an internal representation conceptually equivalent to:

```yaml
request:
  mode:
  granularity:
  output_format:
  target:

table:
  id:
  number:
  title:
  source:
  page_or_location:
  population:
  timepoint:

structure:
  header_rows:
  stub_columns:
  column_hierarchy:
  row_hierarchy:
  continuation_parts:

cells:
  - cell_id:
    row_path:
    column_path:
    raw_text:
    display_precision:
    parsed_type:
    parsed_items:
      - variable:
        category:
        group:
        timepoint:
        statistic:
        estimate_type:
        value:
        lower:
        upper:
        confidence_level:
        unit:
        n:
        semantic_status:
    footnote_markers:
    source_location:
    evidence_status:
    evidence_basis:
    confidence:
      transcription:
      structure:
      interpretation:

footnotes:
  - marker:
    text:
    applies_to:
    source_location:

uncertainties:
  - id:
    location:
    category:
    description:
    alternatives:
    evidence:
    severity:
    required_action:

assumptions:
  - id:
    statement:
    evidence_status:
    scope:
```

The storage format may vary, but preserve the same semantic elements. A displayed cell may contain several results; keep its `raw_text` linked to every parsed item.

### 7.5 Record evidence status

Use:

- `observed`: directly supported by visible text, layout, headers, captions, or footnotes
- `inferred`: derived from identifiable evidence
- `user_confirmed`: explicitly confirmed by the user
- `unresolved`: insufficient evidence to decide

Do not infer a value merely because it is plausible or common. Use `unresolved` when materially plausible alternatives remain.

### 7.6 Resolve semantic identity

Apply this step when the user requests structured, normalized, tidy, machine-readable, analysis-ready, or decomposed output.

#### Statistic first

Identify count, percent, proportion, mean, SD, SE, median, minimum, maximum, quartiles, IQR, estimate, confidence limits, p-value, rate, ratio, risk difference, odds ratio, hazard ratio, survival probability, person-time, or another statistic.

Use the cell, row label, column header, title, caption, footnote, surrounding text, and table-wide convention as evidence.

Do not interpret by numerical shape alone. `12.3 (4.1)` may be mean (SD), estimate (SE), or another paired display.

#### Unit or scale second

Identify years, months, days, kg, mg/dL, `/μL`, percent, score points, events per person-year, dimensionless ratio, or another unit or scale.

Inherit a unit from a grouped row, column, caption, or footnote only when its scope is clear.

Use:

- `unitless` for a dimensionless result
- `not_applicable` when measurement unit does not apply
- `unresolved` when the unit or scale is ambiguous

Do not leave an ambiguous unit silently blank.

#### Contributing N third

Define `N` as the sample size that contributed to calculation of that statistic.

Do not silently equate it with the randomized population, analysis population, treatment-group total, event count, model N, or nearest displayed N unless the source supports that interpretation.

Do not attach the nearest N when missing values or item-specific denominators may make it inapplicable.

An unresolved N does not alone prevent interpretation when statistic and unit are clear. Preserve it as `unresolved`, `unavailable`, or `not_applicable` when N belongs in the output.

### 7.7 Interpret common displays conservatively

#### Count and percentage

For `23 (41.8)` or `23 (41.8%)`, split into count and percentage only when the context supports that convention. Do not infer the denominator unless explicit or uniquely recoverable; mark an inferred denominator and preserve its evidence.

#### Mean and dispersion

Interpret `12.3 ± 4.1` or `12.3 (4.1)` as mean and SD or SE only when a header, label, footnote, or table-wide convention supports it.

#### Median and interval

Interpret `12.3 [8.2, 16.4]` or `12.3 (8.2–16.4)` as median with IQR or range only when the interval type is identified.

#### Estimate and confidence interval

Interpret `1.23 (0.95–1.55)` as estimate and confidence interval only when supported. Record estimate type and confidence level when stated.

#### P-values

Preserve inequalities and textual forms. Never convert `<0.001` to `0.001` or infer an exact value from a threshold.

#### Blank and missing states

Distinguish where possible:

- source blank
- zero
- missing
- not assessed
- not applicable
- not reported
- suppressed
- unreadable

Do not collapse these states without preserving the original.

### 7.8 Apply the clarification gate

Inspect the whole table before asking questions. First use repeated patterns, headers, captions, footnotes, surrounding text, and table-wide conventions.

Ask only when:

- a materially necessary statistic or unit remains unresolved
- the selected output requires semantic normalization
- no source evidence uniquely resolves the issue

Consolidate questions at the table or pattern level, for example:

> Does `a (b–c)` throughout Table 1 mean median (range), with age expressed in months?

Ask about N only after statistic and unit, and only when N is needed.

Do not block reconstruction or readable cleanup solely because semantic interpretation remains unresolved. If provisional output is requested, retain unresolved items instead of blocking.

When clarification is required:

1. preserve the reconstruction
2. mark affected results `unresolved`
3. ask the smallest consolidated question
4. continue after the answer

### 7.9 Normalize

Tidy output should retain:

- `table_id`
- `row_path` and `column_path`
- `variable`, `category`, `group`, and `timepoint`
- `statistic` and `estimate_type`, when applicable
- `value`, interval limits, and confidence level, when applicable
- `unit`
- `n`, when applicable or requested
- `source_cell` and `source_location`
- `evidence_status` and `semantic_status`

Normalization may flatten headers, expand supported composite cells, standardize statistic names, assign units, convert numeric text, or create one row per atomic result.

Normalization must not delete raw text, conceal unresolved interpretations, present inference as observation, remove footnote relationships, alter displayed precision without preserving it, or silently collapse distinct missing states.

### 7.10 Validate against the source

Before completion, verify:

- all target rows and columns are represented
- spanning headers have the correct scope
- continuation parts are merged correctly
- raw cells remain linked to normalized results
- symbols, inequalities, precision, blanks, and footnotes are preserved
- every atomic result has a source location
- no source result is duplicated or omitted without explanation
- inferred and unresolved items remain labeled

Optional consistency checks may flag, but must not silently repair:

- count-percentage denominator mismatches
- impossible percentages
- reversed interval limits
- subtotal inconsistencies
- inconsistent units within one scope
- duplicated or conflicting labels

## 8. Uncertainty taxonomy

Use the smallest applicable set:

- `source_unreadable`
- `continuation_needed`
- `missing_context`
- `header_scope_ambiguous`
- `cell_scope_ambiguous`
- `composite_cell_ambiguous`
- `statistic_unknown`
- `unit_unknown`
- `contributing_n_unknown`
- `footnote_scope_ambiguous`
- `internal_inconsistency`

For machine-readable or audit-preserving output, record `uncertainties: []` when none apply.

## 9. Output contract

For every substantive result, determine and retain:

- `mode`
- `granularity`
- `target`
- `evidence`
- `uncertainties`
- `assumptions`
- `output`
- `next_step`, when further material or clarification is needed

Expose these fields explicitly in machine-readable or audit-preserving output. In ordinary user-facing output, present them compactly and disclose at least material assumptions, uncertainty, and unresolved items.

### 9.1 Source-faithful reconstruction

Preserve displayed structure, raw cells, composite cells, footnotes, source blanks, and unresolved content. Do not claim every result has been interpreted.

### 9.2 Readable cleanup

Improve layout and consistency while preserving meaning. Disclose material ambiguity without forcing decomposition.

### 9.3 CSV-compatible wide format

Keep a structure close to the display; composite cells may remain intact. Because CSV cannot fully preserve merged cells, footnotes, or linked tables, provide a companion note or separate file when necessary.

### 9.4 Tidy analytical format

Use one row per atomic result and link every row to its source cell. Do not emit ambiguous interpretation as resolved.

Example:

```csv
table_id,row_path,column_path,variable,category,group,timepoint,statistic,value,unit,n,evidence_status,source_cell
T1,Sex/Male,Placebo,Sex,Male,Placebo,,count,23,persons,55,observed,cell_0043
T1,Sex/Male,Placebo,Sex,Male,Placebo,,percent,41.8,percent,55,observed,cell_0043
```

### 9.5 Excel output

Use only the sheets needed from:

- `Source_Reconstruction`
- `Readable_Cleanup`
- `Tidy_Data`
- `Footnotes`
- `Issues`
- `Metadata`

Default rules:

- make `Source_Reconstruction` primary unless tidy output is explicitly requested
- preserve raw text and displayed precision
- keep footnotes and unresolved issues visible
- use stable column names and no merged cells in `Tidy_Data`
- freeze headers and use readable widths when practical

### 9.6 JSON or YAML output

Use a TableSpec-compatible representation and preserve hierarchy, raw cells, parsed items, source links, evidence, footnotes, assumptions, and uncertainty.

### 9.7 Audit-preserving output

Additionally retain exact source location, evidence basis, separate confidence dimensions, interpretation alternatives, footnote relationships, user confirmations, issues, and required actions.

## 10. Completion rules

A `source_reconstruction` task is complete when:

1. the target table is identified
2. row and column structure is reconstructed
3. raw displayed cells remain available
4. footnotes and material ambiguities are preserved
5. evidence states remain distinguishable
6. no unsupported values are invented

A `readable_cleanup` task additionally requires:

7. readability is improved without altering meaning
8. layout decisions are consistent
9. unresolved semantic content remains disclosed

An `analysis_ready_tidy` task additionally requires:

10. every result is linked to its hierarchy and variable or outcome
11. every atomic numerical result has an explicit statistic
12. every atomic result has a unit, scale, `unitless`, or `not_applicable` status
13. contributing N is recorded when applicable and available, or visibly marked unresolved or unavailable
14. materially ambiguous statistics or units are resolved through evidence or clarification
15. every normalized result links to its source cell and location
16. no output is described as analysis-ready while required clarification remains outstanding

Do not stop reconstruction merely because interpretation is unresolved. Do not simulate certainty when the source is unreadable, incomplete, or inconsistent.

## 11. Failure-prevention rules

Never:

- flatten before understanding hierarchy
- identify a statistic from numerical shape alone
- convert `<0.001` to `0.001`
- attach the nearest N without evidence
- infer a denominator merely because it is plausible
- treat every blank as missing
- overwrite source precision
- correct suspected errors without preserving the original
- remove footnotes after extracting values
- describe visual cleanup as analysis-ready
- convert every request into tidy data
- ask cell-by-cell questions when one pattern-level question suffices
- abandon reconstruction because interpretation is incomplete

## 12. Example requests

- Read this table.
- Reconstruct the row and column structure.
- Convert this table to CSV without changing the layout.
- Clean up this table for presentation.
- Convert this table into tidy data.
- Separate `n (%)` into count and percentage.
- Identify the statistics, units, and contributing N in each row.
- Extract Table 1 from this article.
- Preserve all footnotes and annotations.
- Identify ambiguous or unreadable cells.
- Produce a clean Markdown table.
- Produce an Excel workbook with source and tidy sheets.
- Explain what each column and statistic represents.
- Reconstruct the table shell in this SAP.
- List all statistics used in the first three tables.

## 13. Version 0.4.1 design

Version 0.4.1 integrates a thin natural-language router with the full semantic reconstruction engine. The router selects mode and granularity; the semantic engine remains authoritative for whether a result may be interpreted, normalized, or described as analysis-ready.

It adds conservative CSV and Excel defaults, mode aliases for backward compatibility, a unified TableSpec and output contract, pattern-level clarification, explicit uncertainty categories, and source-linked completion gates.

---
name: draftcostsheet
description: Draft traceable, reproducible medical-cost sheets from a disease or treatment name, protocol, trial concept, treatment schedule, or existing cost estimate. Use when Codex needs to estimate or compare per-patient drug, hospitalization, examination, procedure, supportive-care, or total medical costs; resolve jurisdiction, valuation basis, and time horizon; retrieve authoritative current unit costs; harmonize currencies or comparison bases; and document resource quantities, sources, assumptions, cost coverage, and unresolved items. Do not use for QALY or ICER estimation, full cost-effectiveness analysis, societal or productivity-loss analysis, lifetime disease modeling, or trial-budget estimation unless the request is explicitly limited to their medical-cost components.
---

# draftcostsheet
**Version 0.2.2**

Part of the **Giant Salamander Skillbox --- Supporting Validated, Trustworthy Science with AI**

## 1. Purpose
`draftcostsheet` drafts a traceable medical-cost sheet from treatment, clinical, or study information. Inputs may range from a disease or treatment name to a protocol, trial concept, treatment schedule, or existing cost estimate.

The central question is:

> What medical cost can be estimated reproducibly from the available
> information, using appropriate resource quantities,
> jurisdiction-appropriate unit-cost sources, an explicit time horizon,
> and visible assumptions?

The skill primarily estimates protocol-defined or otherwise explicitly specified medical costs. It does not automatically perform QALY/ICER estimation, full cost-effectiveness analysis, societal or productivity-loss analysis, lifetime disease modeling, or trial-budget estimation.

## 2. Core principles
Use \(C=\sum_j q_jp_j\), where \(q_j\) is resource quantity and \(p_j\) is unit cost.

Determine the treatment/strategy, cost type, jurisdiction, scope, resource quantities, valuation basis, time horizon, cost coverage, comparison compatibility, and unresolved items.

Prefer a partial but traceable estimate over a complete-looking estimate based on unsupported assumptions. Do not confuse calculation precision with adequacy of cost coverage. Do not infer jurisdiction from language alone.

## 3. Cost-estimate classification
Every material estimate must be interpretable using:

> `cost_type × valuation_basis × time_horizon`

and must have a resolved or explicitly unresolved `jurisdiction`.

### 3.1 cost_type
Use one primary value:

-   `drug`
-   `hospitalization`
-   `examination`
-   `procedure`
-   `supportive_care`
-   `medical_total`
-   `other`

Use `medical_total` only when included resources reasonably capture the major cost drivers for the stated scope and horizon.

### 3.2 valuation_basis
Use one primary value:

-   `drug_price`
-   `reimbursement`
-   `DPC`
-   `provider_cost`
-   `market_price`
-   `mixed`
-   `other`

When `mixed` is used, identify which resources use which valuation basis.

### 3.3 time_horizon
Use `fixed`, `expected`, or `lifetime`.

`fixed` includes a prespecified period or episode such as 1 administration, 1 cycle, 1 course, 4 weeks, 4 calendar months, 1 admission, 1 procedure, or 1 year.

Use `expected` only when the estimate reflects expected treatment duration or resource use. A median duration multiplied by a cost rate is not automatically an expected-cost estimate.

Use `lifetime` when the horizon extends over remaining lifetime. Always state the lifetime estimation method. A simple projection using mean life expectancy is not a fully modeled expected lifetime cost.

### 3.4 jurisdiction
`jurisdiction` identifies the health-care system or geographic market whose prices, reimbursement rules, and costing conventions apply.

Resolve it from, in order:

1.  explicit user specification,
2.  supplied study/protocol context,
3.  source materials clearly identifying the costing system,
4.  other unambiguous contextual evidence.

Do not infer jurisdiction solely from user language, currency preference, nationality, location metadata, or prior unrelated examples. If jurisdiction materially affects an actual monetary estimate and remains unresolved, use the single clarification turn.

### 3.5 Supporting attributes
Retain when relevant: `horizon_detail`, `estimation_method`, `perspective`, `costing_date`, and `currency`.

## 4. Minimal internal data model
Construct these records before finalizing a material estimate. They need not be displayed unless useful or requested.

```text
CostEstimate
- estimate_id
- cost_type
- valuation_basis
- time_horizon
- horizon_detail
- estimation_method
- jurisdiction
- perspective
- costing_date
- value
- currency
- resolution
- resource_item_ids[]
- assumptions[]
- limitations[]
```

Allowed `resolution`: `resolved`, `partially_resolved`, `unsolved`.

```text
ResourceItem
- resource_id
- name
- quantity
- quantity_unit
- unit_cost
- currency
- valuation_basis
- source_id
- provenance
```

Allowed `provenance`: `input`, `retrieved`, `derived`, `assumed`, `unsolved`.

```text
SourceRecord
- source_id
- source_role
- source_type
- title
- organization
- effective_date
- retrieval_date
- locator
- verification_status
```

Allowed `source_role`: `resource_use`, `unit_cost`, `duration`, `clinical_choice`, `currency_conversion`, `other`.

Allowed `source_type`: `official_primary`, `authoritative_secondary`, `clinical_source`, `assumption`.

Allowed `verification_status`: `retrieved`, `unavailable`, `not_required`.

A time-sensitive unit cost or exchange rate is not externally verified unless the relevant source was actually accessed during the current costing task.

## 5. Workflow
> Input → Resolve jurisdiction and target → Harmonize comparison basis
> when needed → Clarify once if needed → Retrieve → Calculate → Check
> coverage → Check comparison → Report

Do not require protocol-level detail before starting.

## 6. Understand and resolve
Identify when possible: disease/clinical situation, treatment/comparison, cost type, scope, valuation basis, jurisdiction, perspective, costing date, horizon, and costing unit.

Default to per-patient costing unless another unit is specified. Do not assume that "treatment cost" means drug cost, procedure fee, hospitalization cost, or total medical cost.

Resolve information in this order: user input → supplied documents → deterministic derivation → authoritative external sources.

When the user specifies a disease but not a treatment, identify a representative current treatment from authoritative clinical sources. Do not silently convert uncertain clinical choices into facts. Handle materially different valid alternatives as scenarios when practical.

## 7. Clarification gate
Ask only when an unresolved specification materially changes the primary estimate or interpretation and cannot be reliably resolved.

Possible topics include jurisdiction, scope, treatment, comparator, reference patient, horizon, costing unit, material alternatives, or cross-jurisdiction valuation concept.

If clarification is required, ask at most once, combine material questions, preferably ask no more than 1--3 questions, and provide reasonable defaults when useful. After that turn, proceed without repeated clarification loops. Preserve remaining uncertainty as an assumption or `UNSOLVED`.

## 8. Costing scope and reference patient
Include only resources relevant to the stated purpose: drug acquisition, administration, supportive care, hospitalization, procedures, radiation, examinations, and surveillance.

Do not automatically include conditional adverse-event treatment, unplanned hospitalization, rescue treatment, or post-progression treatment unless required by the target.

When resource use depends on body weight, BSA, renal function, or another characteristic, prefer study-specific values, then closely related clinical data, authoritative evidence, and finally explicit planning assumptions. Do not silently invent a standard patient.

## 9. Source selection by information type
Select sources according to the information role.

### 9.1 Resource use and treatment specification
For dose, schedule, treatment-duration rules, required supportive care, and protocol-defined examinations, prefer:

1.  supplied protocol or study document,
2.  official regulatory label/product information,
3.  authoritative guideline,
4.  relevant clinical-trial publication,
5.  another authoritative clinical source.

For protocol-specific costing, the supplied protocol takes precedence over a generic label when they differ legitimately.

### 9.2 Unit cost
For time-sensitive monetary values, prefer:

1.  jurisdiction-specific official primary pricing or reimbursement source,
2.  jurisdiction-specific authoritative governmental or professional secondary source,
3.  another authoritative pricing source when the official source is unavailable,
4.  explicit assumption only when defensible and appropriate.

The unit-cost source must match jurisdiction, valuation basis, costing date, currency, and resource definition.

Do not use a foreign unit-cost source merely because it is easier to retrieve. Do not use model memory as evidence for a time-sensitive unit cost. Search snippets, commercial summaries, general websites, and aggregators may support discovery or cross-checking but should not be the primary evidence when an applicable official source is available.

### 9.3 Expected duration and persistence
For expected treatment duration, discontinuation, persistence, or survival-weighted resource use, prefer:

1.  target-population evidence,
2.  closely matched clinical-trial or observational evidence,
3.  justified model-based estimates,
4.  explicit assumptions.

Do not substitute OS for treatment duration, PFS for treatment duration, or median duration for expected duration without explicit justification.

### 9.4 Clinical choice
When selecting a representative treatment, product, or strategy, prefer:

1.  supplied protocol or user-specified option,
2.  current authoritative guideline,
3.  regulatory indication,
4.  current standard-practice evidence,
5.  relevant contemporary clinical literature.

Do not choose a treatment solely because its price is easy to find. When the user asks for the cheapest option, first establish the clinically eligible comparison set.

### 9.5 Source hierarchy within a role
Within the same role, prefer:

`official_primary` → `authoritative_secondary` → `clinical_source` → `assumption`.

A lower-ranked source may be used when a higher-ranked source is unavailable, the lower-ranked source contains required protocol-specific information, the costing concept requires it, or the limitation is explicitly documented.

Do not combine incompatible sources to create a complete-looking estimate.

## 10. Source freshness and execution integrity
For time-sensitive monetary estimates, use values applicable to the costing date whenever feasible, record effective date/version when relevant, and actually access the supporting source during the current task.

Do not imply that a price, fee schedule, tariff, or exchange rate was verified unless the relevant source was actually accessed.

If external access is unavailable, continue non-monetary resource-use resolution where possible, do not substitute remembered monetary values, and mark the affected estimate `UNSOLVED` or `PARTIALLY RESOLVED`.

## 11. Cross-jurisdiction valuation harmonization
For cross-jurisdiction comparisons, define the comparison concept before selecting unit-cost sources whenever feasible.

Use this sequence:

1.  define the common costing target,
2.  identify the most conceptually comparable valuation basis available in each jurisdiction,
3.  select jurisdiction-specific sources for that valuation concept,
4.  harmonize time horizon, perspective, currency treatment, and relevant resource scope,
5.  classify the comparison as compatible, conditional, or incompatible.

### 11.1 Default valuation concept
Default to:

> the closest available public-payer reimbursement or publicly
> administered price concept appropriate to the clinical setting and
> population.

For drugs, prefer a public-payer or publicly administered drug-price concept over a commercial list price when a sufficiently comparable public-payer measure is available.

For procedures, hospitalization, and examinations, prefer the closest broadly applicable public reimbursement or tariff concept.

The selected payer mechanism must be clinically relevant to the population; do not select a payer merely because its data are easy to retrieve.

### 11.2 When public-payer concepts are unavailable or not comparable
If sufficiently comparable public-payer valuation concepts are unavailable:

-   use the closest defensible valuation concept,
-   state the mismatch,
-   retain each jurisdiction's valuation basis,
-   classify the comparison as `conditional`.

Use list-price or market-price comparison when explicitly requested, when public-payer comparison is unavailable, or when list/acquisition price is itself the target.

Do not silently describe a list-price comparison as a public-payer cost comparison.

## 12. Currency conversion and price-year alignment
When currency conversion is required:

-   align the exchange-rate date or period with the costing date or price year whenever feasible,
-   state the exchange-rate source and date/period,
-   preserve the original-currency estimate,
-   report the converted value as a derived comparison value.

For current-cost comparisons, a current or appropriately recent market exchange rate may be used when no other basis is specified.

Do not use current spot FX for historical costs without justification. Do not treat exchange-rate conversion as equivalent to inflation adjustment, PPP, or health-care price adjustment. Use PPP only when requested or methodologically appropriate and label it explicitly.

If price years differ materially, align or qualify them before interpreting relative costs.

## 13. Existing estimates and alternative scenarios
If supplied material contains an existing monetary estimate or relative-cost statement:

1.  do not copy it without verification,
2.  reconstruct the calculation when feasible,
3.  separate resource-use assumptions from unit costs,
4.  verify time-sensitive unit costs,
5.  recalculate using values appropriate to the costing date and jurisdiction,
6.  determine whether the original statement remains valid.

Correct arithmetic does not imply that an estimate remains current.

Do not silently collapse materially different valid alternatives such as protocol-permitted regimens, targeted agents, originator/biosimilar products, or reimbursement pathways. Clarify when selection is necessary or report important alternatives as scenarios.

## 14. Drug costing
Resolve:

> dose → required quantity → product units → cost per administration →
> interval or horizon cost

Use clinically appropriate product handling. Default to full-unit costing without vial sharing unless another rule is specified.

When multiple strengths exist, prefer:

1.  protocol- or label-specified handling,
2.  established clinical use,
3.  a feasible low-cost combination.

Preserve natural clinical units such as per administration, per cycle, and per course.

## 15. Costing time unit
For recurring treatment, use cost per week as the default internal standardized rate when a common comparison unit is needed.

Preserve the natural clinical unit. For comparison:

\[
C_{4w}=4C_{\mathrm{week}}
\]

may be reported as a standardized average cost rate.

Do not interpret this automatically as exact resource use during a particular 28-day period. Do not equate 4 weeks with 1 calendar month, 4 months with 16 weeks, or 1 cycle with 1 month. Interpret months as calendar months unless otherwise defined.

Do not force non-recurring interventions into weekly units; use per procedure, per admission, or per treatment episode.

## 16. Time-horizon rules
For `fixed`, state the exact period or episode.

For `expected`, state how expected duration or expected resource use was derived. Do not use `expected` merely because a median duration was available.

For `lifetime`, state how survival and treatment persistence were handled. Label simple projections explicitly.

If a broader horizon cannot be supported, report identifiable fixed-horizon costs and mark the broader estimate `UNSOLVED`.

Treatment duration and costing horizon are different concepts.

## 17. Hospitalization, examination, procedure, and radiation
For hospitalization, use a coherent admission-level valuation approach such as DPC, reimbursement, or provider cost. Do not assume a procedure fee represents total hospitalization cost.

For examinations:

\[
C_{\mathrm{exam}}=\sum_j N_jp_j
\]

where `N_j` is the number of examinations.

For procedures, use one coherent valuation method and preserve the natural episode unit.

For radiation, use a representative internally coherent reimbursement pathway; the natural unit is usually one treatment course.

## 18. Aggregation
For each strategy:

\[
C=\sum_j q_jp_j
\]

Keep major cost types separate when useful. Use `medical_total` only when the combined components adequately represent the intended total medical-cost scope.

Do not infer cost-effectiveness from cost alone.

## 19. Comparison compatibility
Before comparing CostEstimate records, assess compatibility across:

-   cost type,
-   valuation basis,
-   time horizon and detail,
-   jurisdiction,
-   perspective,
-   costing date,
-   currency or price year,
-   resource scope,
-   reference-patient assumptions,
-   estimation method.

A comparison is generally compatible when these are aligned or validly standardized.

A conditional comparison may proceed when differences are intentional and interpretable, such as originator versus biosimilar, q2w versus q3w standardized to weekly cost, or different price dates after explicit adjustment.

Do not directly interpret as equivalent: drug cost versus total medical cost; procedure reimbursement versus hospitalization provider cost; fixed 4-week versus lifetime cost; different jurisdictions without valid harmonization; or materially different valuation concepts without a bridge.

Instead construct compatible estimates, present them separately, or state that direct comparison is not interpretable.

## 20. Incremental, relative, lowest-cost, and highest-cost claims
Before reporting:

\[
\Delta C=C_A-C_B
\]

or

\[
R_C=\frac{C_A}{C_B}
\]

confirm comparison compatibility and identify numerator/new treatment, denominator/comparator, jurisdiction, cost type, valuation basis, horizon, and material patient/product assumptions.

Before claiming an option is lowest- or highest-cost:

1.  define the clinically relevant comparison set,
2.  obtain or account for every material eligible option,
3.  confirm compatibility,
4.  align jurisdiction, cost type, valuation basis, horizon, perspective, currency, and costing date,
5.  qualify the conclusion if a relevant option remains unresolved.

Do not state that an option is the cheapest when relevant alternatives could not be valued.

Prefer:

> Among the clinically eligible and comparable options with resolved
> current costs, Option A had the lowest estimated cost.

## 21. Cost-coverage check
Before finalizing, ask:

> Does the calculated estimate adequately represent what the user is
> calling "cost"?

Drug cost may adequately represent a drug-price comparison but poorly represent intensive inpatient chemotherapy. Procedure reimbursement may poorly represent total surgical hospitalization cost. Examination cost may adequately represent a surveillance-strategy comparison.

If important cost drivers are excluded:

-   do not call the result overall treatment cost,
-   state that coverage is limited,
-   identify major omitted components,
-   retain the narrower cost type.

Do not automatically broaden scope merely because coverage is limited.

## 22. Completion gates
Before finalizing a `RESOLVED` CostEstimate, confirm:

1.  `cost_type` is assigned.
2.  `valuation_basis` is assigned.
3.  `time_horizon` is assigned.
4.  `jurisdiction` is assigned when jurisdiction-specific monetary costing is performed.
5.  Every material ResourceItem has a quantity.
6.  Every material ResourceItem has a unit cost.
7.  Every retrieved time-sensitive unit cost has a SourceRecord.
8.  Unit-cost SourceRecords are compatible with jurisdiction and valuation basis.
9.  Required external sources were actually retrieved during the current task.
10. The CostEstimate value reconciles with its ResourceItems.
11. Material assumptions are recorded.
12. Cost coverage has been assessed.
13. Partial components are not presented as total medical cost.
14. Important unresolved items are visible.

For comparative conclusions additionally confirm:

15. comparison compatibility has been assessed.
16. cross-jurisdiction valuation harmonization was attempted when applicable.
17. the comparison set is sufficiently complete for lowest/highest-cost claims.
18. currency conversion and price-year handling are explicit when applicable.

If these conditions are not met, use `PARTIALLY RESOLVED` or `UNSOLVED`, provide the calculable partial result, and do not fabricate missing values.

## 23. Per-patient versus trial-level cost
Default to per-patient cost.

Do not multiply per-patient cost by sample size and label it trial budget unless trial-level expenditure is explicitly requested.

Trial-budget estimation may require actual treatment duration, discontinuation, sponsor-covered treatment, research-only procedures, site payments, and operational costs.

## 24. Output
Adapt detail to the request. The default output should remain compact.

- **Estimate classification:** cost type, valuation basis, time horizon, jurisdiction, horizon detail, and estimation method when material.
- **Costing target:** treatment/comparison, perspective, costing date, and scope.
- **Key assumptions:** only assumptions that materially affect cost.
- **Resource table:**

| Resource | Unit cost | Quantity | Cost | Source |
| --- | ---: | ---: | ---: | --- |

- **Calculation:** enough intermediate calculation to reproduce the estimate.
- **Cost summary:** only relevant values, such as per administration, cycle, week, 4 weeks, procedure, admission, fixed horizon, expected horizon, lifetime, incremental, or relative cost.
- **Coverage and limitations:** major omitted cost drivers, unresolved items, and interpretation limits.
- **Sources:** traceable sources for important monetary inputs.

Use precise labels. Do not call drug acquisition cost total treatment cost, a procedure reimbursement fee total hospitalization cost, a fixed-horizon estimate expected cost, or a simple lifetime projection a fully modeled expected lifetime cost. Do not compare jurisdiction-specific costs as directly equivalent without harmonization, replace `UNSOLVED` with an arbitrary estimate, or infer cost-effectiveness from cost alone.

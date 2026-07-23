---
name: reviewcitation
description: "Review citations in scientific documents for citation integrity: reconcile in-text and reference-list entries, apply Vancouver-style checks, perform required PubMed verification, and flag inconsistencies and publication-status signals. Externally verified claims must reflect current-review access and evidence."
---

# REVIEWCITATION

**Version 0.3.3**

Part of the **Giant Salamander Skillbox — Supporting Validated, Trustworthy Science with AI**

## 1. Purpose

REVIEWCITATION performs a lightweight, evidence-based review of citations in scientific documents.

The central question is:

> Are the citations complete, traceable, bibliographically accurate, consistently formatted, and not materially inconsistent with the statements they accompany?

Its primary output is a review report that identifies:

- citation-numbering and reference-list problems
- departures from the applicable Vancouver-style convention
- missing, duplicated, unused, or unmatched references
- bibliographic discrepancies identified through PubMed
- unavailable or unresolved bibliographic records
- retraction, correction, erratum, or related-publication signals when identifiable
- statements that appear inconsistent with cited titles or abstracts
- citations that cannot be assessed from the available evidence
- user decisions or source materials required to complete the review

REVIEWCITATION supports **Citation Integrity**: the completeness, traceability, bibliographic accuracy, and contextual consistency of citations.

Unless the user explicitly requests otherwise, REVIEWCITATION verifies every reference expected to be indexed in PubMed against PubMed metadata within the requested scope. A reference is not considered externally verified unless the corresponding external source was actually accessed during the current review and the access is recorded in the execution-proof record.

It does not determine whether a scientific claim is true, whether a study is methodologically sound, whether the total evidence is sufficient, or whether a conclusion should be accepted.

## 2. Scope and boundaries

Use REVIEWCITATION for:

- journal manuscripts
- review articles
- clinical-trial protocols
- Statistical Analysis Plans
- general analysis plans
- clinical study reports and technical reports
- grant applications
- theses and dissertations
- conference abstracts and proceedings
- research guidance documents
- other scientific documents containing in-text citations and a reference list

Use REVIEWCITATION when the primary task is to assess citation integrity.

REVIEWCITATION may review one citation, a selected section, or an entire document.

For a clinical-trial SAP review, use `REVIEWSAP`.

For a general analysis-plan or coding-specification review, use `REVIEWAPLAN`.

For reconstruction or semantic normalization of a visually complex table, use `READATABLE`.

Use `SAMPLESIZE200` for sample-size, event, power, or detectable-effect calculations.

REVIEWCITATION does not replace:

- formal editorial review
- journal-specific reference-style review by the publisher
- systematic-review methods
- evidence grading
- risk-of-bias assessment
- peer review of scientific validity
- full-text verification when only titles or abstracts are available
- human responsibility for final citation approval

## 3. Review modes

Identify the requested review mode before applying the workflow.

### 3.1 Citation structure review

Review the internal correspondence between in-text citations and the reference list.

This mode includes:

- citation numbering
- first-appearance order
- duplicate or reused numbers
- missing numbers
- in-text citations without reference-list entries
- reference-list entries not cited in the document
- citation ranges and grouped citations
- repeated citations to the same reference

### 3.2 Vancouver-style review

Review whether citations and references follow the applicable Vancouver-style policy.

This mode includes:

- numeric citation style
- numbering by first appearance
- author-name presentation
- article-title presentation
- journal-title abbreviation
- publication year, volume, issue, and page or article number
- DOI or PMID presentation when required by the selected policy
- punctuation and element order
- formatting of books, chapters, online resources, reports, and other reference types when identifiable

Vancouver style is a family of related conventions, not one perfectly uniform journal format.

Distinguish:

- a general Vancouver-style review
- a named journal's instructions for authors
- a user-supplied house style

Do not label a reference incorrect merely because it differs from one Vancouver variant when the applicable policy is unknown.

### 3.3 Bibliographic verification

PubMed verification is enabled by default.

For every reference within the requested scope that is reasonably expected to be indexed in PubMed, actually access PubMed during the current review, match the reference to a record, and compare the supplied metadata with the matched metadata.

Skip default PubMed verification only when the user explicitly requests one of the following:

- a `Quick` review
- a document-only review
- a formatting-only review
- no external search
- review of material for which PubMed verification is not applicable

Review:

- PMID
- DOI
- title
- authors
- journal
- publication year
- volume, issue, pages, or article identifier
- publication type
- linked correction, erratum, expression of concern, or retraction information when available

Use other supplied authoritative metadata when PubMed is not applicable or does not contain the record.

Do not treat absence from PubMed as proof that a publication does not exist.

### 3.4 Title-and-abstract consistency review

Compare the statement associated with a citation against the cited publication's title and abstract.

The purpose is to detect material inconsistency, not to prove support or scientific truth.

This mode may identify discrepancies involving:

- study population
- intervention or exposure
- comparator
- outcome
- direction of association or treatment effect
- study design
- diagnostic target
- time frame
- subgroup
- numerical result explicitly stated in the abstract
- publication type
- claim strength

Do not claim full-text verification unless the full text was actually supplied or reviewed.

### 3.5 Review profiles and routing

Review modes define **what domains are reviewed**. Review profiles define **how broadly and deeply the selected modes are applied**.

Use one profile:

| Profile | Default scope and depth |
|---|---|
| `Targeted` | Review only the explicitly identified citation, section, reference subset, or document region. PubMed verification remains enabled by default for every eligible reference in that target unless the user explicitly disables external verification |
| `Quick` | Review document-internal citation structure and dominant Vancouver-style patterns only. Do not perform routine external verification unless the user specifically requests it or an obvious identity conflict cannot otherwise be described |
| `Standard` | Review all requested document-internal domains and verify every eligible reference in scope against PubMed. Perform title-and-abstract review only for citations selected by explicit reproducible signals or user focus |
| `Full` | Apply all requested modes to the complete requested scope, verify every eligible reference against PubMed, and review every available title and abstract for which claim mapping and evidence are sufficient |

Apply these routing rules:

1. Use `Targeted` when the user limits the document scope to a citation, section, subset, attachment, or other explicit region.
2. Use `Quick` only when the user asks for a quick, preliminary, screening, document-only, formatting-only, or no-external-search review.
3. Use `Standard` when the user asks to review citations, check references, assess Vancouver style, verify a complete reference list, or otherwise requests a review without limiting it to `Quick`.
4. Use `Full` when the user requests a comprehensive, exhaustive, complete, all-citation, or all-abstract review.
5. A request limited to one review mode does not by itself require `Targeted`; profile is determined primarily by document scope and requested depth.
6. Full-text review is never implied by `Full`; it remains a separate evidence level and requires supplied or actually accessed full text.

Record the selected profile, requested modes, document scope, PubMed-verification policy, external-verification execution status, and any sampling or selection rule used for title-and-abstract review.

Do not silently review only a subset while presenting the result as a complete review.

### 3.6 Default PubMed verification policy

Unless the user explicitly disables external verification, apply these rules:

- verify every eligible reference in the requested scope against PubMed
- do not silently sample eligible references
- if the requested scope is the complete document, verify all eligible references or explicitly list the references not completed
- check linked correction, erratum, expression-of-concern, retraction, and related-publication signals when available in PubMed
- use PubMed metadata as the primary external source for PubMed-indexed biomedical literature
- use authoritative non-PubMed sources for records that are not applicable to PubMed or cannot be resolved there
- do not treat absence from PubMed as evidence that the publication does not exist

External verification is disabled only by an explicit user instruction such as:

- `quick review`
- `document only`
- `formatting only`
- `do not search externally`
- `do not use PubMed`

When external verification is disabled, set the affected verification level to `Document only` and do not report suspected external discrepancies as verified facts.

### 3.7 Mandatory reference-level PubMed assessment

For every supplied reference in the requested scope, construct exactly one `PubMedAssessment` record, including references that are not expected to be indexed in PubMed.

The assessment ledger is the authoritative record of PubMed verification. Aggregate statements such as `four records were searched` or `three records matched` are summaries derived from the ledger and are not execution evidence by themselves.

Use only these `pubmed_status` values:

- `indexed`
- `no_matching_record_found`
- `multiple_candidates`
- `not_applicable_to_pubmed`
- `unresolved`
- `not_searched`

Apply these rules:

- Use `indexed` only when a specific PubMed record was actually retrieved during the current review and uniquely matched to the supplied reference.
- Use `no_matching_record_found` when an actual PubMed search was performed using a reasonable search sequence but no plausible matching record was identified. This does **not** prove that the item is not indexed in PubMed.
- Use `multiple_candidates` when two or more plausible PubMed records remain.
- Use `not_applicable_to_pubmed` for source types not reasonably expected to have a PubMed record, such as many government reports, product documents, institutional policies, books, websites, and unpublished materials.
- Use `unresolved` when eligibility, identity, or search interpretation cannot be determined.
- Use `not_searched` when no PubMed search was performed for that reference.

When `pubmed_status = indexed`, the record must contain:

- PMID
- matched title
- match classification
- retrieval source actually accessed
- evidence identifier from the current retrieval
- retraction-status assessment
- linked retraction-notice PMID or DOI when present

Use only these `retraction_status` values:

- `no_retraction_link_found`
- `retracted`
- `retraction_notice_found`
- `expression_of_concern_found`
- `correction_only`
- `unresolved`
- `not_assessed`

Interpret them conservatively:

- `no_retraction_link_found` means no retraction notice, retraction link, or retracted-publication signal was identified in the PubMed record reviewed at the time of assessment. It does not certify that no retraction exists elsewhere or will appear later.
- `retracted` means the matched publication is identified as retracted in the reviewed PubMed evidence.
- `retraction_notice_found` means a retraction-notice record was identified but the status or linkage of the intended original publication requires separate explanation.
- `expression_of_concern_found` means an expression-of-concern signal was identified.
- `correction_only` means a correction or erratum was identified without a retraction signal.
- `unresolved` means the available record did not permit a defensible classification.
- `not_assessed` is required when no PubMed record was retrieved or publication status was not reviewed.

A `Standard` or `Full` review is not complete unless:

- `reference_count = pubmed_assessment_record_count`; and
- every reference has one and only one assessment record; and
- every PubMed-eligible reference has a `pubmed_status` other than `not_searched`; and
- every `indexed` record includes a PMID and current-review evidence identifier; and
- every `retracted` record includes a retraction-notice identifier when one is available.

Do not describe an item as `not indexed in PubMed` merely because no match was found. Report `no_matching_record_found` and retain the actual search basis.

### 3.8 External-verification execution state

When bibliographic verification is required, initialize the external-verification execution status as `pending`.

Use only these execution statuses:

- `pending`: external verification is required but has not yet been executed
- `completed`: the required external sources were actually accessed during the current review and all eligible records were processed or explicitly accounted for
- `explicitly disabled`: the user explicitly requested a Quick, document-only, formatting-only, or no-external-search review
- `unavailable`: external access was attempted or required but could not be used
- `partial`: external access occurred, but not every eligible record was processed; the unprocessed denominator and records must be listed

A `pending` or `partial` status is not equivalent to completed PubMed verification.

If the selected profile requires PubMed verification and the execution status remains `pending`, do not finalize the report as a completed `Standard` or `Full` review. Either:

1. execute the required external verification; or
2. issue a `Document-only partial review`, mark bibliographic and publication-status domains `Cannot assess` or `Not performed` as appropriate, and state that PubMed verification remains pending.

Do not convert `pending` to `completed` merely because corrected metadata is known or appears plausible.

## 4. Core principles

### 4.1 Citation integrity, not scientific truth

The primary object of review is the citation relationship.

Do not determine:

- whether the scientific claim is true
- whether the cited study is high quality
- whether the evidence is sufficient
- whether another study would be a better citation
- whether the manuscript's conclusion should be believed

Instead determine whether the citation is complete, traceable, bibliographically accurate, and not materially inconsistent with the available title or abstract.

### 4.2 No evidence, no citation-specific assertion

Every citation-specific finding must be supported by identifiable evidence.

Evidence may come from:

- the supplied document
- the reference list
- PubMed metadata
- PubMed title or abstract text
- a supplied full-text article
- a supplied journal style guide
- user confirmation

Do not invent missing reference elements, PMIDs, DOIs, author names, titles, publication details, or article content.

### 4.3 Separate verification layers

Keep the following layers distinct:

1. document structure verification
2. style review
3. bibliographic verification
4. title-and-abstract consistency review
5. full-text review, only when full text is available and requested

A citation may pass one layer and remain unresolved or problematic in another.

For example, a reference may be correctly formatted but linked to the wrong article.

### 4.4 Use conservative consistency judgments

Do not infer contradiction merely because the abstract does not explicitly repeat the manuscript statement.

Absence of confirmation is not contradiction.

Use an inconsistency judgment only when the available title or abstract provides affirmative evidence that materially conflicts with the associated statement.

### 4.5 Preserve source wording and traceability

For every reviewed citation, preserve or record:

- citation number or citation key
- associated manuscript statement
- reference-list entry
- source location
- matched bibliographic record
- verification source
- evidence level
- finding and rationale

Do not detach a citation finding from the statement and location to which it applies.

### 4.6 Distinguish global and local style problems

A repeated formatting pattern is usually a document-level issue rather than dozens of separate reference-level issues.

Consolidate systematic style findings, such as:

- all journal titles are unabbreviated
- all references list every author when the selected policy limits authors
- all DOI formats use a nonconforming prefix

Report individual references only when they differ from the dominant pattern or require separate correction.

### 4.7 Keep the review proportionate

REVIEWCITATION is a focused citation review.

Do not expand it into a manuscript-wide scientific review, systematic review, or methodological consultation unless the user explicitly requests another skill or task.

### 4.8 Use deterministic review decisions

For the same materials and requested scope, the review should apply the same routing, matching, classification, and reporting rules.

Before producing findings:

- resolve the review profile and modes
- construct the citation and reference records
- preserve the basis for every bibliographic match
- assign claim-to-citation mapping confidence
- distinguish domain-level non-review from citation-level inability to assess
- apply issue severity only after the evidence and affected object are identified

Do not allow output length, document size, or tool availability to change an unstated review rule. When a practical limitation requires partial processing, state the selection rule and reviewed denominator.


### 4.9 External verification integrity

Do not state or imply that PubMed, Crossref, a publisher, a journal, a registry, or another external source was checked unless that source was actually accessed during the current review.

Do not provide externally verified bibliographic metadata from memory.

For every external verification claim, preserve:

- source actually accessed
- identifier or search basis used
- matched record
- match status
- verification level reached
- unresolved ambiguity

If external access fails or is unavailable:

- continue the document-internal review
- classify the external layer as `Cannot assess`
- do not substitute remembered metadata
- do not fabricate a supporting link or citation
- state which eligible references remain unverified

A correct-looking bibliographic statement is not `verified` unless the source was actually accessed in the current review.

### 4.10 Reference-level, tool-grounded execution proof

Before reporting any externally verified finding, construct the complete `PubMedAssessment` ledger for the supplied references in scope.

A valid external-verification claim requires record-level retrieval evidence produced during the current review. Self-reported fields such as `external_source_accessed = yes`, `records_queried = 4`, a remembered PMID, or a plausible corrected citation are not execution proof.

For each supplied reference, preserve:

- `reference_id`
- supplied reference text
- PubMed eligibility
- `pubmed_status`
- search query, identifier, or search basis actually used
- PubMed record actually retrieved, when any
- PMID, when indexed
- matched title
- match classification
- `retraction_status`
- linked retraction-notice PMID or DOI, when any
- source actually accessed
- access method
- current-review evidence identifier
- unresolved ambiguity

Construct `ExternalVerificationRun` only after the assessment ledger exists. Its counts must be derived from the ledger, not independently generated.

Apply these rules:

1. Every supplied reference must have exactly one `PubMedAssessment` record.
2. `pubmed_status = indexed` is invalid without a PMID and a current-review evidence identifier tied to the retrieved PubMed record.
3. `pubmed_status = no_matching_record_found` is invalid unless an actual search basis is recorded.
4. `retraction_status = no_retraction_link_found`, `retracted`, `retraction_notice_found`, `expression_of_concern_found`, or `correction_only` is invalid unless a PubMed record or linked-publication evidence was actually reviewed.
5. If no externally retrieved source evidence exists in the current review, set all PubMed-eligible references to `not_searched`, set retraction status to `not_assessed`, and do not finalize a completed `Standard` or `Full` report.
6. A generic search-result page does not by itself verify every reference. Preserve record-level evidence for each `indexed` assessment.
7. A model-memory answer, an unexecuted intended search, or a fabricated raw link does not count as source access.
8. Aggregate counts must reconcile exactly with the reference-level ledger.
9. Every Major or Critical externally derived issue must identify the supporting `PubMedAssessment` and its evidence identifier.
10. If an assessment cannot be completed, retain `unresolved` or `not_searched`; do not create a complete-looking record from memory.

## 5. Inputs

Use the following inputs when available.

| Input | Purpose |
|---|---|
| Document or manuscript | Provides the statements, in-text citations, and source locations |
| Reference list | Provides bibliographic entries to reconcile and verify |
| User request | Defines review mode, scope, and desired output |
| Journal instructions | Defines the applicable Vancouver variant or house style |
| Citation manager export | Supports structured reconciliation and metadata checking |
| PMID, DOI, or other identifier | Supports precise bibliographic matching |
| PubMed metadata | Supports bibliographic verification and title/abstract review |
| Supplied article full text | Supports optional full-text review when explicitly requested |
| Prior review report | Identifies unresolved discrepancies and corrections |
| User clarification | Resolves uncertain matches, style policies, or intended citations |

The document and reference list are the primary inputs.

PubMed access is required for PubMed-based bibliographic verification and abstract review. When it is unavailable, perform the document-internal review and mark external verification `Cannot assess`.

### 5.1 Internal review data model

Construct the following internal records before final reporting. The records do not need to be displayed unless the user requests a complete matrix or machine-readable output.

#### `CitationOccurrence`

- `occurrence_id`
- `citation_label` or citation number
- `source_location`
- `claim_unit_id`
- `citation_group_id`, when applicable
- `raw_citation_text`

#### `ClaimUnit`

- `claim_unit_id`
- `exact_or_preserved_text`
- `source_location`
- `claim_scope`: sentence / clause / numeric statement / list item / paragraph
- `mapping_confidence`: high / moderate / low / unresolved

#### `ReferenceEntry`

- `reference_id`
- `reference_list_position`
- `supplied_entry`
- `reference_type`, when identifiable
- `cited_status`

#### `PubMedAssessment`

- `reference_id`
- `supplied_entry`
- `eligibility_for_pubmed`: eligible / not applicable / unresolved
- `pubmed_status`: indexed / no_matching_record_found / multiple_candidates / not_applicable_to_pubmed / unresolved / not_searched
- `search_basis`
- `search_terms_or_identifier_used`
- `matched_pmid`
- `matched_title`
- `match_classification`: exact / probable / multiple candidates / none / not applicable / unresolved
- `retraction_status`: no_retraction_link_found / retracted / retraction_notice_found / expression_of_concern_found / correction_only / unresolved / not_assessed
- `retraction_notice_identifier`
- `matched_source`
- `access_method`
- `evidence_identifier`
- `unresolved_ambiguity`

#### `ExternalVerificationRun`

- `external_verification_required`
- `execution_status`: pending / completed / explicitly disabled / unavailable / partial
- `reference_count`
- `pubmed_assessment_record_count`
- `external_source_accessed`
- `sources_accessed`
- `access_method`
- `records_eligible`
- `records_indexed`
- `records_no_matching_record_found`
- `records_multiple_candidates`
- `records_not_applicable`
- `records_unresolved`
- `records_not_searched`
- `unverified_reference_ids`
- `evidence_identifiers`
- `counts_derived_from_pubmed_assessments`: yes / no

#### `BibliographicMatch`

- `reference_id`
- `pubmed_assessment_reference`
- `eligibility_for_pubmed`: eligible / not applicable / unresolved
- `external_access_status`: accessed / not accessed by explicit user instruction / unavailable
- `match_status`
- `matched_identifier`
- `matched_source`
- `match_basis`
- `verified_metadata`
- `verification_level`
- `unresolved_ambiguity`

#### `ConsistencyAssessment`

- `claim_unit_id`
- `reference_id` or `citation_group_id`
- `status`
- `evidence_status`
- `verification_level`
- `evidence_reviewed`
- `rationale`

#### `Issue`

- `issue_id`
- `domain`
- `severity`
- `affected_object`
- `finding`
- `evidence`
- `required_action`

Maintain separate records for citation occurrences and unique references. Do not collapse repeated citation occurrences when their associated statements or locations differ.

## 6. Workflow and review checks

### 6.1 Resolve profile, modes, and scope

Determine:

- review profile: `Targeted`, `Quick`, `Standard`, or `Full`
- review modes: citation structure, Vancouver-style compatibility, bibliographic verification, title-and-abstract consistency, or a combination
- document scope: one citation, selected references, one section, or the complete document
- PubMed-verification policy: enabled by default / explicitly disabled / unavailable
- external-verification execution status: pending / completed / explicitly disabled / unavailable / partial
- output depth: compact report, full report, complete matrix, or corrected reference list

Apply the routing rules in Sections 3.5 and 3.6. Construct the `ExternalVerificationRun` record before assigning any externally verified status.

### 6.1.1 Reference-level PubMed gate before final reporting

Before finalizing the report:

1. count all supplied reference entries in scope;
2. confirm that exactly one `PubMedAssessment` exists for each reference;
3. verify that `reference_count = pubmed_assessment_record_count`;
4. verify that every PubMed-eligible reference has a status other than `not_searched`;
5. verify that every `indexed` assessment includes a PMID, matched title, retraction status, and current-review evidence identifier;
6. verify that every `no_matching_record_found` assessment records the actual search basis;
7. verify that all aggregate counts in `ExternalVerificationRun` are derived from and reconcile with the assessment ledger;
8. list every unresolved, multiple-candidate, or not-searched reference.

If external verification is required and any PubMed-eligible reference remains `not_searched`, do not issue a completed `Standard` or `Full` report. Execute the search or downgrade the output explicitly to `Document-only partial review`.

If any reference lacks a `PubMedAssessment`, do not report a complete reference-level review.

If `execution_status = partial`, do not describe the eligible set as fully verified. State the complete reference denominator and list every incomplete assessment.

If `execution_status = unavailable`, continue the document-internal review but set PubMed-eligible records to `not_searched` or `unresolved`, set retraction status to `not_assessed`, and mark the external domain `Cannot assess`.

If `execution_status = explicitly disabled`, produce one assessment row per reference, using `not_searched` for PubMed-eligible references and `not_applicable_to_pubmed` where appropriate. Report `Document only` as the highest verification level.

For a request such as `Review the citations`, `Check the references`, or `Check whether these references follow Vancouver style`, use:

- profile: `Standard`
- modes: the requested mode plus bibliographic verification
- scope: the complete supplied document and every reference list within it
- PubMed verification: enabled for every eligible reference
- output: compact report with the mandatory reference-level PubMed assessment table

If the user identifies one citation, section, attachment, or subset, use `Targeted` and produce one assessment record for every reference in that target.

Do not assume full-text review.

### 6.2 Identify the review target and materials

Record:

- document title or description
- version or date, when available
- sections reviewed
- reference list reviewed
- journal or style policy used
- PubMed verification status and any user-requested exception
- external sources actually accessed during the current review
- eligible references not externally verified
- full texts supplied or reviewed
- materials unavailable
- review limitations

Do not imply that inaccessible references or full texts were reviewed.

### 6.3 Extract and reconcile citation structure

Identify:

- every in-text citation occurrence
- its source location
- citation number, number range, or citation key
- the associated statement or sentence
- every reference-list entry
- reference-list order

Check:

- whether numbering follows first appearance
- whether citation ranges are valid
- whether the same number consistently identifies the same reference
- whether all in-text citations map to a reference-list entry
- whether every reference-list entry is cited
- whether duplicate entries refer to the same publication
- whether apparent duplicates contain materially different metadata
- whether numbering has gaps or unexplained resets

Do not automatically merge apparent duplicate references when uncertainty remains.

### 6.4 Determine the applicable citation policy

Assign one policy profile:

- `journal_specific`
- `institutional_house_style`
- `user_supplied`
- `general_nlm`

Use the following priority:

1. user-supplied journal or institutional instructions
2. explicitly named citation policy
3. user-supplied house style
4. `general_nlm`, based on the current applicable edition of NLM *Citing Medicine*

Document-wide convention may be used to identify systematic patterns, but it is not an authoritative policy when it conflicts with a supplied instruction or with the declared `general_nlm` profile.

When a named journal style is not supplied, describe findings as compatibility with `general_nlm` Vancouver style rather than exact journal compliance.

Record:

- policy profile
- policy source
- policy version or access date when available
- unresolved journal-specific requirements

Do not classify a difference between Vancouver variants as an error unless the applied policy resolves that difference.

### 6.5 Review Vancouver-style presentation

Review the relevant reference types and citation presentation.

For journal articles, check when applicable:

- author surnames and initials
- number of authors displayed and use of `et al.`
- article title
- journal title or standard abbreviation
- year
- volume
- issue, when required
- page range or article number
- DOI or PMID, when required
- punctuation and order

For other source types, check the elements required by the applicable policy, such as:

- editors
- book title
- edition
- place of publication
- publisher
- chapter pages
- report number
- organization
- access date
- URL
- preprint server
- dataset or software version

Do not force a journal-article template onto a different source type.

### 6.6 Produce one PubMed assessment for every reference

Create the `PubMedAssessment` ledger in reference-list order. Do not omit non-PubMed source types.

For each reference:

1. classify PubMed eligibility;
2. if eligible and external verification is enabled, actually search PubMed during the current review;
3. preserve the identifier or search terms used;
4. assign one allowed `pubmed_status`;
5. if indexed, preserve the PMID, matched title, match classification, and current-review evidence identifier;
6. inspect the matched record and linked-publication information for retraction, expression-of-concern, and correction signals;
7. assign one allowed `retraction_status`;
8. retain any linked retraction-notice identifier and unresolved ambiguity.

Search eligible records using available information in this order where practical:

1. PMID
2. DOI
3. exact normalized title
4. near-exact title with first author, journal, and year
5. author, journal, year, volume, and pages or article identifier
6. partial bibliographic matching

Use these assessment decisions:

| PubMed status | Decision rule | Required evidence |
|---|---|---|
| `indexed` | One retrieved PubMed record uniquely identifies the supplied reference | PMID, matched title, match classification, and current-review evidence identifier |
| `no_matching_record_found` | An actual reasonable search found no plausible record | Search basis and current-review search evidence |
| `multiple_candidates` | Two or more plausible records remain | Candidate identifiers and unresolved basis |
| `not_applicable_to_pubmed` | The source type is not reasonably expected to have a PubMed record | Reference-type rationale |
| `unresolved` | Eligibility or identity cannot be determined defensibly | Limitation and available evidence |
| `not_searched` | No PubMed search was performed | Reason search was not performed |

For `indexed` records, classify bibliographic matching as:

- `exact`
- `probable`
- `multiple candidates`
- `unresolved`

Additional rules:

- A PMID or DOI resolving to another publication is not an exact match; report an identifier conflict.
- Minor punctuation, capitalization, diacritic, pagination normalization, or electronic-versus-print date differences do not prevent an exact identity match.
- Do not promote a probable match to exact merely because only one result appeared.
- Do not use `no_matching_record_found` to claim that PubMed does not index the item.
- Do not use remembered bibliographic details as a substitute for current retrieval.
- Do not silently sample eligible references.
- The final report must contain exactly one assessment row per supplied reference.

### 6.7 Compare bibliographic metadata

For matched records, compare the supplied reference with PubMed metadata.

Check:

- title
- authors
- journal
- publication year
- volume and issue
- pages or article identifier
- DOI
- PMID
- publication type

Distinguish:

- stylistic differences
- harmless normalization differences
- substantive bibliographic discrepancies

Examples of substantive discrepancies include:

- wrong article title
- wrong first author
- wrong publication year that identifies another article
- DOI belonging to another publication
- PMID belonging to another publication
- incorrect journal
- reference assembled from elements of different publications

Do not treat capitalization or punctuation normalization as a substantive discrepancy unless the applicable style requires correction.

### 6.8 Assign retraction and related-publication status

For every `indexed` PubMed assessment, inspect the publication type, record notices, and linked-publication relationships actually visible in the retrieved PubMed evidence.

Assign exactly one `retraction_status`:

| Retraction status | Meaning |
|---|---|
| `no_retraction_link_found` | No retraction notice, retraction link, or retracted-publication signal was identified in the reviewed PubMed evidence at the time of review |
| `retracted` | The intended publication is identified as retracted |
| `retraction_notice_found` | A retraction-notice record was identified, but the intended original-publication relationship requires explanation |
| `expression_of_concern_found` | An expression-of-concern signal was identified |
| `correction_only` | A correction, erratum, or corrected-and-republished relationship was identified without a retraction signal |
| `unresolved` | The available PubMed evidence does not permit a defensible classification |
| `not_assessed` | No PubMed record or publication-status evidence was reviewed |

Record linked notice identifiers when available.

Do not state simply that an article `has not been retracted`. Use the narrower wording represented by `no_retraction_link_found`.

Do not infer the meaning or consequence of a correction, expression of concern, or retraction beyond the available evidence.

### 6.9 Identify the cited statement

For every citation selected for consistency review, identify the smallest meaningful associated statement.

A citation may support:

- the complete sentence
- one clause
- one numerical statement
- one item in a list
- a paragraph-level background statement

When multiple citations follow one statement, treat them as a citation group first. Do not assume each reference independently supports every element of the statement.

When one citation is attached to several claims, separate the claims where necessary.

Assign `mapping_confidence`:

| Confidence | Meaning |
|---|---|
| `high` | The citation is directly attached to one clearly bounded statement or claim |
| `moderate` | The citation probably applies to the identified statement, but nearby text or grouped citations introduce limited ambiguity |
| `low` | The citation may apply to several sentences, clauses, or list items and the intended mapping is uncertain |
| `unresolved` | The available formatting or context does not permit a defensible claim-to-citation mapping |

Do not classify a citation as `Inconsistent` when mapping confidence is `low` or `unresolved`. Use `Potential inconsistency` or `Cannot assess`, and explain the mapping limitation.

### 6.10 Compare the statement with title and abstract

Compare the associated statement against the matched publication's title and abstract.

Assess only information visible in the reviewed evidence.

Check for material consistency involving:

- population
- intervention or exposure
- comparator
- outcome
- direction
- magnitude when explicitly available
- study design
- time point or follow-up
- subgroup
- diagnostic or prognostic purpose
- causal versus associational language
- primary versus secondary outcome
- review versus original research

Use the following consistency statuses:

| Status | Meaning |
|---|---|
| `No inconsistency identified` | No material conflict was identified from the reviewed title and abstract |
| `Potential inconsistency` | A material difference may exist, but ambiguity or incomplete abstract evidence prevents a firm judgment |
| `Inconsistent` | The reviewed title or abstract affirmatively conflicts with a material element of the associated statement |
| `Cannot assess` | The citation could not be matched, no abstract was available, the statement was too broad or unclear, or the issue requires full text |
| `Not reviewed` | Consistency review was outside the requested scope |

Do not use `No inconsistency identified` to mean that the publication proves or fully supports the statement.

### 6.11 Apply claim-strength safeguards

Flag potential inconsistency when the manuscript statement materially exceeds what the title or abstract reports, for example:

- association described as causation
- no statistically significant effect described as a demonstrated benefit
- secondary or exploratory result described as the primary finding
- a subgroup result generalized to the full population
- one outcome replaced by another
- feasibility evidence described as effectiveness evidence
- an observational study described as a randomized trial

Use conservative wording.

Do not flag merely because the manuscript paraphrases the abstract differently.

### 6.12 Assign issue severity

Use:

| Severity | Meaning |
|---|---|
| `Critical` | The citation identifies the wrong publication, a retracted publication is used without acknowledgment where materially relevant, or a clear contradiction could substantially mislead the reader |
| `Major` | Correction or clarification is required to restore citation identity, traceability, or material contextual consistency |
| `Minor` | A formatting or metadata correction is needed but does not materially change citation identity or meaning |
| `Note` | A limitation, uncertainty, style preference, or useful observation |

Systematic style problems may be reported as one consolidated issue.

Assign issue IDs by domain:

- `STR-###`: citation structure
- `STY-###`: citation or reference style
- `BIB-###`: bibliographic identity or metadata
- `PUB-###`: retraction, correction, erratum, or related-publication status
- `CON-###`: statement-to-citation consistency
- `UNR-###`: unresolved identity, mapping, or evidence limitation requiring visibility

Severity is a separate field and is not encoded in the issue ID.

### 6.13 Determine review judgment

Use one overall judgment:

- `Pass within reviewed scope`
- `Conditional pass`
- `Revision required`
- `Cannot assess`

Apply these rules:

- A Critical issue normally implies `Revision required`.
- A Major issue normally implies `Revision required` or `Conditional pass`, depending on scope and impact.
- Minor style issues alone normally imply `Conditional pass`.
- Notes alone may be consistent with `Pass within reviewed scope`.
- `Pass within reviewed scope` is allowed only when the reviewed profile, modes, scope, denominators, and unreviewed domains are stated clearly.
- A domain may be `Cannot assess` without forcing the overall review to `Cannot assess` when the remaining requested domains were assessable and the limitation is explicit.
- Use overall `Cannot assess` when the primary requested review cannot be performed or the document-reference relationship cannot be reconstructed sufficiently to support a judgment.
- Do not use numeric scoring.

## 7. Evidence and clarification rules

### 7.1 Evidence vocabulary

Use:

| Evidence status | Meaning |
|---|---|
| `observed` | Directly visible in the supplied document, reference list, source, title, abstract, or metadata |
| `inferred` | Derived from identifiable evidence but not directly stated |
| `user_confirmed` | Explicitly confirmed by the user |
| `unresolved` | Insufficient evidence to determine the item |

For inferred findings, preserve the evidence basis.

Do not present inferred or unresolved information as observed fact.

### 7.2 Verification level

Record the highest verification level actually reached:

- `Document only`
- `Bibliographic metadata verified`
- `Title verified`
- `Abstract reviewed`
- `Full text reviewed`
- `Cannot assess`

Do not label a citation `Bibliographic metadata verified`, `Title verified`, `Abstract reviewed`, or `Full text reviewed` unless the corresponding source was actually accessed during the current review.

Do not label a citation `Full text reviewed` when only PubMed metadata, title, abstract, or a publisher landing page was reviewed.

### 7.3 Evidence rule

For each material finding, identify evidence such as:

- manuscript section, paragraph, sentence, or page
- citation number
- reference-list number
- quoted statement or concise paraphrase
- PMID or DOI
- PubMed record
- title or abstract passage
- supplied journal style rule
- explicit absence of an expected reference entry

Avoid vague findings such as `citation seems wrong` or `reference may not support this`.

State:

- what differs
- where it differs
- what evidence was reviewed
- why the difference matters
- what action is required

### 7.4 Clarification gate

Inspect the complete supplied citation context and reference list before asking questions.

Use identifiers, repeated citation patterns, document-wide style, surrounding sentences, and PubMed candidate records before requesting clarification.

Ask only when the unresolved issue materially affects citation identity, style assessment, or consistency review.

Consolidate related questions.

Examples:

- Which journal's Vancouver variant should be applied?
- Does citation 18 intend the 2019 original article or the 2021 correction?
- Is reference 27 intentionally uncited, or should it be linked to the preceding paragraph?

Do not ask the user to confirm information already supplied clearly.

### 7.5 Multiple citations and composite statements

When a statement cites several references:

- review the citation group before assigning individual responsibility
- identify which component of the statement each citation appears to address when possible
- avoid declaring one reference inconsistent merely because another reference in the group provides the relevant evidence
- mark the mapping unresolved when individual support cannot be assigned from the available context

### 7.6 No-abstract and non-PubMed records

When no abstract is available:

- perform bibliographic verification where possible
- use the title only for limited inconsistency detection
- mark abstract-level consistency `Cannot assess`

For records with `no_matching_record_found` or `not_applicable_to_pubmed`:

- do not treat absence of a matching PubMed record as an error
- use supplied identifiers or authoritative metadata when available
- clearly identify the source used
- mark unavailable verification layers `Cannot assess`
- do not rewrite `no_matching_record_found` as `not indexed in PubMed`

Use this source priority when external verification is within scope:

1. DOI registration metadata or another authoritative identifier registry
2. official publisher, journal, society, or conference record
3. official government, university, international organization, repository, or report page
4. authoritative library catalogue
5. user-supplied source document or metadata export
6. other sources only when necessary, with the limitation stated explicitly

Do not combine metadata from different candidate records to create a complete-looking reference.

## 8. Output

The default output is a compact **REVIEWCITATION Report**. Use a full report when the user requests it, when a complete audit trail is needed, or when the number and complexity of findings cannot be represented safely in the compact report.

### 8.1 Compact report

Use this format by default:

```markdown
# REVIEWCITATION Report

## Review scope

- Skill version:
- Review profile:
- Document and sections reviewed:
- Review modes:
- Citation policy:
- Review completion status: completed / Document-only partial review / external-verification partial
- External verification required: yes / no
- PubMed verification policy: enabled / explicitly disabled / unavailable
- External source accessed: yes / no
- External-verification execution status: pending / completed / explicitly disabled / unavailable / partial
- External sources actually accessed:
- Access method:
- Eligible PubMed references:
- Records queried:
- PubMed assessment rows:
- Records indexed / no matching record / multiple candidates / not applicable / unresolved / not searched
- Eligible references not verified:
- Evidence identifiers:
- Full texts reviewed:
- Material limitations:

## Overall judgment

Judgment: Pass within reviewed scope / Conditional pass / Revision required / Cannot assess

Rationale:
- ...

## Domain summary

| Domain | Status | Reviewed denominator or scope | Summary |
|---|---|---|---|
| Citation structure | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... | ... |
| Vancouver-style compatibility | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... | ... |
| Bibliographic accuracy | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... | ... |
| Publication-status signals | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... | ... |
| Title-and-abstract consistency | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... | ... |

## Reference-level PubMed assessment

Include exactly one row for every supplied reference in scope.

| Reference | PubMed eligibility | PubMed status | PMID | Match classification | Retraction status | Retraction-notice identifier | Search basis | Evidence identifier |
|---|---|---|---|---|---|---|---|---|
| 1 | eligible / not applicable / unresolved | indexed / no_matching_record_found / multiple_candidates / not_applicable_to_pubmed / unresolved / not_searched | ... | exact / probable / multiple candidates / none / not applicable / unresolved | no_retraction_link_found / retracted / retraction_notice_found / expression_of_concern_found / correction_only / unresolved / not_assessed | ... | ... | ... |

The number of rows must equal the number of supplied references.

## Issues requiring attention

| ID | Citation or pattern | Severity | Finding | Evidence status | Verification level | Evidence identifier | Required action |
|---|---|---|---|---|---|---|---|
| STR-001 / STY-001 / BIB-001 / PUB-001 / CON-001 / UNR-001 | ... | Critical / Major / Minor / Note | ... | observed / inferred / user_confirmed / unresolved | ... | ... | ... |

## Cannot-assess items and clarification

- ...

## Recommended next actions

1. ...
2. ...
```

### 8.2 Full report

Use this format when a full report is requested or justified:

```markdown
# REVIEWCITATION Report

## 1. Review scope

- Skill: REVIEWCITATION
- Skill version:
- Review profile:
- Document reviewed:
- Document version or date:
- Sections reviewed:
- Reference list reviewed:
- Review modes:
- Citation policy applied:
- Review completion status: completed / Document-only partial review / external-verification partial
- External verification required: yes / no
- PubMed verification policy: enabled / explicitly disabled / unavailable
- External source accessed: yes / no
- External-verification execution status: pending / completed / explicitly disabled / unavailable / partial
- External sources actually accessed:
- Access method:
- Eligible PubMed references:
- Records queried:
- PubMed assessment rows:
- Status counts: indexed / no matching record / multiple candidates / not applicable / unresolved / not searched
- Eligible references not verified:
- Evidence identifiers:
- Full texts reviewed:
- Materials unavailable:
- Review limitations:

## 2. Overall judgment

Judgment: Pass within reviewed scope / Conditional pass / Revision required / Cannot assess

Brief rationale:
- ...

## 3. Citation integrity summary

| Domain | Status | Summary |
|---|---|---|
| Citation structure | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... |
| Vancouver-style compatibility | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... |
| Bibliographic accuracy | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... |
| Publication-status signals | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... |
| Title-and-abstract consistency | OK / Needs clarification / Problem / Cannot assess / Not reviewed | ... |

## 4. Reconciliation summary

- In-text citation occurrences:
- Unique citation numbers or keys:
- Reference-list entries:
- Unmatched in-text citations:
- Uncited reference-list entries:
- Duplicate or probable duplicate entries:
- Numbering or ordering problems:
- PubMed assessment rows:
- Indexed records:
- No matching record found:
- Multiple-candidate records:
- Not applicable to PubMed:
- Unresolved records:
- Not searched:
- Abstracts reviewed:

Counts are descriptive only and are not a score.

## 5. Reference-level PubMed assessment ledger

Include exactly one row per supplied reference.

| Reference | Supplied entry | Eligibility | PubMed status | PMID | Matched title | Match classification | Retraction status | Retraction-notice identifier | Search basis | Evidence identifier | Unresolved issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ... | ... | eligible / not applicable / unresolved | indexed / no_matching_record_found / multiple_candidates / not_applicable_to_pubmed / unresolved / not_searched | ... | ... | exact / probable / multiple candidates / none / not applicable / unresolved | no_retraction_link_found / retracted / retraction_notice_found / expression_of_concern_found / correction_only / unresolved / not_assessed | ... | ... | ... | ... |

The ledger is incomplete if the row count does not equal the supplied-reference count.

## 6. Issues requiring attention

| ID | Citation or pattern | Severity | Domain | Finding | Evidence status | Verification level | Evidence identifier | Required action |
|---|---|---|---|---|---|---|---|---|
| STR-001 / STY-001 / BIB-001 / PUB-001 / CON-001 / UNR-001 | ... | Critical / Major / Minor / Note | ... | ... | observed / inferred / user_confirmed / unresolved | ... | ... | ... |

If none:

No citation-integrity issues were identified from the reviewed materials.

## 7. Bibliographic discrepancies

| Citation | Match status | Supplied entry | Verified metadata | Discrepancy | Verification level |
|---|---|---|---|---|---|
| ... | Exact / Probable / Multiple candidates / No match / Not applicable / Cannot assess | ... | ... | ... | ... |

If none:

No substantive bibliographic discrepancies were identified.

## 8. Potential title-or-abstract inconsistencies

| Citation | Associated statement | Status | Evidence reviewed | Reason | Required action |
|---|---|---|---|---|---|
| ... | ... | Potential inconsistency / Inconsistent / Cannot assess | Title / Abstract / Full text | ... | ... |

Do not list citations classified only as `No inconsistency identified` unless the user requests a complete matrix.

If none:

No material title-or-abstract inconsistencies were identified from the reviewed evidence.

## 9. Cannot-assess items

| Citation or item | Missing evidence | Why assessment is limited |
|---|---|---|
| ... | ... | ... |

If none:

No Cannot-assess items were identified.

## 10. Required clarification questions

1. ...
2. ...
3. ...

If none:

No clarification questions are required to complete the requested review.

## 11. Recommended next actions

1. ...
2. ...
3. ...

## 12. Handoff

Next recommended step:
- ...

Information to pass forward:
- ...

Unresolved issues to carry forward:
- ...

Suggested next prompt:
- ...
```

### 8.3 Default reporting behavior

By default:

- use the compact report
- state the selected review profile, modes, exact scope, review completion status, whether external verification was required, PubMed-verification policy, whether an external source was accessed, and external-verification execution status
- include exactly one `PubMedAssessment` row for every supplied reference
- state the external sources actually accessed, access method, reference-level evidence identifiers, and total reference denominator
- derive all aggregate counts from the reference-level assessment ledger
- never infer external-verification counts from the reference-list length alone
- never treat aggregate counts as a substitute for reference-level evidence
- use `no_matching_record_found`, not `not indexed in PubMed`, unless non-indexing is independently established
- list any eligible references not externally verified
- label the output `Document-only partial review` when PubMed verification was required but not executed
- require evidence status, verification level, and evidence identifier for every Major or Critical externally derived issue
- report the denominator for each reviewed domain when meaningful
- report any selection rule used for title-and-abstract review
- report global Vancouver-style patterns once
- report unmatched, duplicated, and materially discrepant references individually
- report only `Potential inconsistency`, `Inconsistent`, and `Cannot assess` items in the detailed consistency table
- omit citations for which no inconsistency was identified from the detailed table
- state the number of titles, abstracts, and full texts reviewed
- preserve citation numbers, claim locations, and mapping limitations
- use `Pass within reviewed scope`, never an unqualified `Pass`
- omit the Handoff section unless another skill, reviewer, or subsequent workflow is materially relevant

### 8.4 Complete citation matrix

When the user requests a complete citation matrix, include one row per unique citation with:

| Citation | Source location | Associated statement | Mapping confidence | Reference entry | PubMed status | PMID | Retraction status | Retraction-notice identifier | DOI | Style status | Bibliographic status | Consistency status | Verification level | Evidence identifier | Finding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Do not present the matrix as a numeric scorecard.

### 8.5 Corrected reference list

Produce a corrected reference list only when requested.

When doing so:

- apply the selected style policy consistently
- preserve unresolved entries visibly
- do not fabricate missing bibliographic elements
- separate verified corrections from proposed corrections
- label uncertain matches

### 8.6 Suggested replacement wording

Draft replacement manuscript wording only when requested.

Label it:

`Proposed - not source-specified or author-approved`

Do not rewrite scientific claims merely to make them agree with a citation unless the user asks for editing support.

## 9. Completion and stopping rules

A REVIEWCITATION task is complete when:

1. the review profile, target, scope, requested modes, and output depth are identified
2. the applicable citation policy is identified or the `general_nlm` policy is declared
3. in-text citations and reference-list entries are reconciled for the requested scope
4. citation-structure problems are identified
5. Vancouver-style compatibility is reviewed when requested
6. exactly one `PubMedAssessment` record exists for every supplied reference in scope
7. `reference_count = pubmed_assessment_record_count`
8. every PubMed-eligible reference has a status other than `not_searched`, unless external verification was explicitly disabled or unavailable
9. every `indexed` assessment includes PMID, matched title, match classification, retraction status, and current-review evidence identifier
10. every `no_matching_record_found` assessment records the actual search basis
11. aggregate external-verification counts are derived from and reconcile with the assessment ledger
12. material bibliographic discrepancies are identified
13. publication-status signals are reported conservatively using the allowed retraction statuses
14. selected statements are compared with titles and abstracts when requested
15. consistency judgments do not exceed the reviewed evidence
16. evidence and verification levels are recorded
17. unresolved and Cannot-assess items remain visible
18. clarification questions are consolidated
19. recommended actions are provided
20. no scientific claim is declared true or false solely through this skill
21. no numeric citation-quality score is used
22. the denominator and selection rule are stated for any partially reviewed domain
23. claim-to-citation mapping confidence is recorded when consistency review is performed
24. no external source is described as checked unless it was actually accessed during the current review
25. every Major or Critical externally derived issue records evidence status, verification level, and evidence identifier
26. a review requiring PubMed verification is not finalized as completed while any eligible assessment is `not_searched`, missing, or unsupported by current-review evidence

Do not describe the citation review as complete when:

- citation numbering cannot be reconciled because part of the document or reference list is missing
- the applicable style is essential to the request but remains unknown
- a bibliographic match remains materially ambiguous
- a title-or-abstract inconsistency judgment requires unavailable full text
- only a subset was processed but the selection rule or denominator is not recorded
- the number of PubMed assessment rows does not equal the number of supplied references
- any supplied reference lacks a PubMed assessment row
- eligible PubMed references remain `not_searched` without an explicit disabled or unavailable status
- an external verification claim is based on memory rather than current source access
- external-verification execution status is missing, `pending`, or inconsistent with the reported counts
- external-verification counts are reported without reference-level execution evidence
- an `indexed` status lacks a PMID or current-review evidence identifier
- `no_matching_record_found` lacks a recorded search basis
- `no_retraction_link_found` is presented as proof that no retraction exists
- publication-status review is reported as `OK` without actual external source access
- claim-to-citation mapping is unresolved for a material consistency finding

If PubMed verification is required but the assessment ledger is incomplete, apply this stopping rule:

1. do not finalize a completed `Standard` or `Full` report;
2. complete one assessment record for every reference; or
3. downgrade the report to `Document-only partial review`, use `not_searched` or `unresolved` as appropriate, set retraction status to `not_assessed`, and identify every incomplete reference.

Instead:

- complete the assessable review layers
- mark the affected layer or citation `Cannot assess`
- identify the missing evidence
- ask the minimum necessary clarification question when user input can resolve it

Do not stop the entire review merely because some references are not indexed in PubMed or lack abstracts.

Do not infer that a citation is valid because its metadata is correct.

Do not infer that a citation is invalid because PubMed does not contain it.

Do not infer that a claim is supported because no contradiction was found.

## 10. Limitations

A `Pass within reviewed scope` judgment means that no blocking citation-integrity issue was identified within the stated profile, modes, scope, denominators, and evidence layers.

It does not certify that:

- the scientific claims are true
- the evidence is sufficient
- the cited studies are valid or unbiased
- the most appropriate references were selected
- the manuscript is publication-ready
- the reference list complies with every journal-specific production rule
- the full text supports the statement when only the title or abstract was reviewed
- no undisclosed correction, retraction, or indexing problem exists outside the reviewed sources

REVIEWCITATION evaluates citation integrity.

It does not by itself:

- conduct a systematic literature search
- identify all missing citations in the scientific literature
- assess risk of bias
- grade certainty of evidence
- perform plagiarism detection
- review the full scientific argument
- validate numerical analyses
- replace author, editor, librarian, or peer-review judgment

## 11. Example requests

Typical requests include:

- Review the citations in this manuscript using the Standard profile.
- Check whether the references follow Vancouver style; verify all eligible references against PubMed by default.
- Perform a Quick formatting-only review without external search.
- Check citation numbering and reference-list correspondence.
- Find in-text citations that are missing from the reference list.
- Find references that are never cited.
- Verify these references against PubMed.
- Check the DOI, PMID, title, authors, journal, and year.
- Identify duplicate references.
- Report PubMed indexing status and retraction status for every reference.
- Check whether any cited publication has a retraction or correction notice.
- Compare each cited statement with the article title and abstract.
- Identify claims that appear inconsistent with the cited abstract.
- Review citation 12 only.
- Perform a Full review and produce a complete citation matrix.
- Correct the reference list to Vancouver style.
- Review citations in this SAP without reviewing the SAP itself.

## Suggested invocation prompt

```text
You are performing a lightweight, evidence-based citation-integrity review.

Resolve the review profile (`Targeted`, `Quick`, `Standard`, or `Full`), requested modes, exact document scope, PubMed-verification policy, external-verification execution status, and output depth. PubMed verification is enabled by default for every eligible reference in scope. Disable it only when the user explicitly requests a Quick, document-only, formatting-only, or no-external-search review.

If the user asks to review citations, check references, or assess Vancouver style without further restrictions, use the `Standard` profile, review the complete supplied document and all reference lists, and verify every eligible reference against PubMed. If the user limits the scope to a citation, section, attachment, or subset, use `Targeted` and still verify every eligible reference in that target unless explicitly disabled.

Identify the requested review modes: citation structure, Vancouver-style compatibility, bibliographic verification, and title-and-abstract consistency.

Use the rule: citation integrity, not scientific truth. Do not determine whether claims are true, whether studies are high quality, or whether evidence is sufficient.

Reconcile in-text citations with the reference list. Construct separate citation-occurrence, claim-unit, reference-entry, bibliographic-match, consistency-assessment, and issue records. Apply the supplied journal policy when available; otherwise use the `general_nlm` policy based on NLM Citing Medicine.

Create exactly one `PubMedAssessment` record for every supplied reference. Use only `indexed`, `no_matching_record_found`, `multiple_candidates`, `not_applicable_to_pubmed`, `unresolved`, or `not_searched`. Actually access PubMed during the current review before using `indexed`, and require PMID, matched title, match classification, retraction status, and current-review evidence for that row. Use only `no_retraction_link_found`, `retracted`, `retraction_notice_found`, `expression_of_concern_found`, `correction_only`, `unresolved`, or `not_assessed` for retraction status. Do not describe `no_matching_record_found` as proof that a reference is not indexed. Do not provide externally verified metadata from memory. Derive `ExternalVerificationRun` counts from the assessment ledger. If the number of assessment rows differs from the number of supplied references, or any eligible reference remains `not_searched`, do not finalize a completed Standard or Full report; complete the ledger or downgrade the output to `Document-only partial review`.

For title-and-abstract review, detect only material inconsistency. Absence of confirmation is not contradiction. Use `No inconsistency identified`, `Potential inconsistency`, `Inconsistent`, `Cannot assess`, or `Not reviewed`. Never describe `No inconsistency identified` as proof of support.

Use the REVIEWCITATION Report format. Use `Pass within reviewed scope`, never an unqualified `Pass`. Do not use numeric scoring. State the supplied-reference denominator, include the complete reference-level PubMed assessment table, external-verification execution status, sources actually accessed, access method, evidence identifiers, mapping confidence, verification level, and every unresolved or not-searched reference. Consolidate systematic style findings and clarification questions. Do not claim full-text verification unless the full text was actually reviewed.
```

## References

- International Committee of Medical Journal Editors. Recommendations for the Conduct, Reporting, Editing, and Publication of Scholarly Work in Medical Journals.
- National Library of Medicine. Citing Medicine: The NLM Style Guide for Authors, Editors, and Publishers.
- National Center for Biotechnology Information. PubMed and Entrez Programming Utilities documentation.

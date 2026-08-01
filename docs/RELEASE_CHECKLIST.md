# Cross-host release checklist

Release candidate: `skillbox-2026.08.01-rc6`

Cross-host acceptance completed: 2026-08-01

## Automated checks

- [x] deterministic build succeeds twice with identical hashes
- [x] repository release validator passes
- [x] existing three individual ZIP hashes remain unchanged
- [x] OpenAI plugin validator passes for the all-in-one plugin
- [ ] `claude plugin validate --strict` passes
- [x] canonical `skills/` and generated bundle copies are byte-identical
- [x] all four ZIPs are listed in `SHA256SUMS.txt`
- [x] no personal paths, caches, credentials, or compiled artifacts are included

## ChatGPT Work

- [x] install the all-in-one ZIP unchanged
- [x] display name is `Giant Salamander Skillbox`
- [x] `readatable`, `reviewcitation`, and `samplesize200` are available
- [x] run one representative operation for each skill

## Codex

- [x] add the GitHub marketplace
- [x] install `giant-salamander-skillbox@giant-salamander-skillbox`
- [x] start a new task
- [x] invoke `$readatable`, `$reviewcitation`, and `$samplesize200`
- [x] run one representative operation for each skill

## Claude Code

- [x] install the all-in-one ZIP unchanged in Claude Code desktop
- [x] confirm that the installed all-in-one plugin loads and operates
- [x] add the GitHub marketplace
- [x] install `giant-salamander-skillbox@giant-salamander-skillbox`
- [x] run `/reload-plugins`
- [x] invoke each `/giant-salamander-skillbox:<skill-name>` command
- [x] confirm natural-language routing for each skill
- [x] run one representative operation for each skill

## OpenAI submission

- [ ] select the verified developer or business identity
- [ ] confirm `Apps Management: Write` access
- [ ] upload the production logo
- [ ] choose supported countries or regions
- [ ] enter three starter prompts
- [ ] enter five positive and three negative test cases
- [ ] upload the final tested ZIP
- [ ] submit only after the GitHub prerelease and hashes are final

## Publication

- [ ] create the immutable Git tag
- [ ] publish four ZIPs, `SHA256SUMS.txt`, cheat sheet, and release notes
- [ ] download every asset from GitHub Releases and recheck its hash
- [ ] confirm both marketplace entries resolve the release tag
- [ ] update Notion links to the new GitHub Release

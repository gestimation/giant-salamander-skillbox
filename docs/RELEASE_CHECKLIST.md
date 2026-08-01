# Cross-host release checklist

Release candidate: `skillbox-2026.08.02-rc7`

Cross-host acceptance for the previous bundle completed: 2026-08-01

## Automated checks

- [x] deterministic build succeeds twice with identical hashes
- [x] repository release validator passes
- [x] the published readatable and reviewcitation ZIP hashes remain unchanged
- [x] the versioned samplesize200 rc.7 ZIP hash is recorded
- [x] OpenAI plugin validator passes for the all-in-one plugin
- [x] Claude Code desktop installation and execution acceptance recorded; the strict CLI validator was not run
- [x] canonical `skills/` and generated bundle copies are byte-identical
- [x] all four ZIPs are listed in `SHA256SUMS.txt`
- [x] no personal paths, caches, credentials, or compiled artifacts are included

## ChatGPT Work

- [x] install the rc.2 all-in-one ZIP unchanged
- [x] display name is `Giant Salamander Skillbox`
- [x] `readatable`, `reviewcitation`, and `samplesize200` are available
- [x] run one representative operation for each skill

## Codex

- [ ] install the rc.2 all-in-one ZIP unchanged before the rc.7 tag exists
- [ ] start a new task
- [ ] invoke `$readatable`, `$reviewcitation`, and `$samplesize200`
- [ ] run one representative operation for each skill
- [ ] after publication, refresh the GitHub marketplace and confirm the rc.7 tag

## Claude Code

- [x] install the rc.2 all-in-one ZIP unchanged in Claude Code desktop
- [x] confirm that the installed all-in-one plugin loads and operates
- [x] invoke each `/giant-salamander-skillbox:<skill-name>` command
- [x] confirm natural-language routing for each skill
- [x] run one representative operation for each skill
- [ ] after publication, refresh the GitHub marketplace and confirm the rc.7 tag

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

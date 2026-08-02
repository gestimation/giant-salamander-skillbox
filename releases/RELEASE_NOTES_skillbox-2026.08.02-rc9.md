# Giant Salamander Skillbox — 2026.08.02 rc9

This prerelease corrects the English Giant Salamander Skillbox cheat sheet.
The corrected sheet identifies the current all-in-one plugin as
`giant-salamander-skillbox-1.0.0-rc.3.zip`.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.7`

## Scope

- replaces `skillbox-cheatsheet-en.pdf` with the corrected one-page PDF
- republishes the remaining rc8 assets unchanged so rc9 remains a complete
  distribution set
- keeps the all-in-one plugin at `1.0.0-rc.3`
- keeps the Codex and Claude Code marketplace catalogs pinned to rc8 because
  the plugin source and ZIP are byte-identical

No skill instructions, calculation formulas, rounding rules, registered
procedures, numerical results, plugin manifests, or installation ZIPs changed.
The PowerPoint source file is retained as an editing source and is not a public
release asset.

## Assets

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.7.zip` | 118 | 421,101 | `8b2ef987c1dfd1933bfb9b7be321ccbf0bc3bd1dd60405a2a9f5c52bcbead614` |
| `giant-salamander-skillbox-1.0.0-rc.3.zip` | 125 | 450,862 | `193b4ec3ab2c8c00d78746fb4e48a4d65eb3d9a3577d55e22d9ef099671559b7` |
| `skillbox-cheatsheet-ja.pdf` | 1 page | 863,971 | `193e8e6a00d3cbc939174ac5fd3d5eecefc32f0566c79f7455494f92ec05e895` |
| `skillbox-cheatsheet-en.pdf` | 1 page | 560,931 | `70627b08ce98a79937f11269fcef57cd88d7adc16e50c8f5c7601f050d655b64` |
| `samplesize200-cheatsheet-ja.pdf` | 2 pages | 864,377 | `074781e525c88d58ec317c71127b5b9a40e0e63a77cc7c00a44796f21cb619e6` |
| `samplesize200-cheatsheet-en.pdf` | 2 pages | 870,631 | `ad7262a0eec34a36d39e248c7a769ad04c2f3d595b2eeceacefd4d2c17ce6193` |

`SHA256SUMS.txt` is unchanged and continues to contain the hashes for the four
installation ZIPs.

## Validation status

- corrected PDF page count: 1
- corrected PDF text check: `rc.3` present and stale `rc.2` absent
- corrected PDF full-page render and visual review: PASS
- the other three cheat-sheet PDF hashes remain unchanged from rc8: PASS
- all four installation ZIP hashes remain unchanged from rc8: PASS

GitHub Releases is the canonical ZIP and cheat-sheet distribution source.
Published assets are never replaced in place; corrections receive a new release
tag.

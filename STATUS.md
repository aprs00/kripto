HEALTH: OK — system just deployed; main book flat (no strategy has passed the Hyperliquid gate yet), 3 candidates trading in shadow books.

_Updated 2026-11-08 by the setup session._

## Main book ($200 paper)
Flat (cash $200.00). It only trades strategies in `incubation`/`active` (see docs/design.md §4 gates).

## Strategies
| strategy | status | evidence | live shadow |
|---|---|---|---|
| tsmom (trend, L/S) | candidate | BN OOS Sharpe 1.26 (all years +); HL OOS 0.55, grid median 0.89 | starting |
| xsmom | candidate | BN 0.63, HL 0.71 | starting |
| carry (funding) | candidate | BN 1.35 (+15%/yr funding); HL test pending data | starting |
| xsrev, lowvol, funding_contra | rejected | negative after costs | — |

## Key finding
Hyperliquid has the signal (trend price-only Sharpe 1.2) but costs eat most of it, and the $10 minimum order
makes diversified strategies impossible to execute at $200. Research focus: cost reduction + small-account construction.

## Next
HL carry test once funding history finishes downloading; cost-reduction experiments (backlog T1b, T1c).

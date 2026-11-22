# T1i audit (2026-11-22, interactive, independent of the session that produced it). E2 must read this first.
* Order of events: prereg written 20:32:10 UTC, confirmT card 20:32:54, vault card 20:33:52; one run each, no rerun flag. Universe rank uses volume through the previous close (causal).
* Data gaps: 0 of 1,142 fills have a missing minute in the hour before, > 10% zero-volume minutes, or < 10k USD traded in the fill minute. Not an artefact.
* Binance PERCENT_PRICE (how far below mark a bid may rest: 5% BTC/ETH/SOL, 10% DOGE, 15% most alts, from today's exchangeInfo): 3–4% of fills were not allowed. Without them: explore +129, confirmT +198
  (p .016), vault +234 (p .002). **E2: quote min(30 σ, allowed band); skip when 30 σ is outside the band.**
* Independence: 1,142 fills = 608 distinct minutes = 403 days. One vote per day: explore +192 (t 6.2), confirmT +269 (t 4.0), vault +238 bp (t 2.5, 78 days, 81% positive days, median day +217).
* Tail: 2026-06-02 LAB −58% in one hour, 2026-07-24 VELVET −24%. Best 2026 fills are pumped small caps (BTW, AKE, EVAA), not majors: in 2026 the "top 20 by volume" is partly meme coins.
  June 2026 (3 fills) −14.7%, March −0.8%; the other 8 months positive.
* Still unproven and only live paper can show it: that the resting order is really filled at its price in those minutes, and what the hour-later exit costs.
* Earlier pass 2 looked at 2026 lshock results on 83 coins (a related idea): the vault was clean for this rule, not for the family.

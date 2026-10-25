# Arm H item pool (v2): items for spot-check

24 code-analysis items (12 buggy, 12 clean): `task/code-analysis/ca_51`…`ca_74`, manifest `task_manifest_hard24.json`. v2 was revised Oct 25 after calibration pilot 1, in which Sonnet 5 got 7/7 v1 items right. v1 is in git history (commit 2013c7c and the renames after it). No model was called to make v2. **Difficulty is my guess**, not a measurement.

## What the pilot showed, and what v2 does about it

The pilot workers did two things v1 hadn't planned for:

- **They test every clause.** Each docstring clause and example became a small-input assert, including the "in passing" ones (trailing `\n`, Devanagari digits, leap years crossing a year).
- **They read the code and go straight to the suspicious line.** Examples: `start.year`, `_can_cover`, `sorted(words)`.

So a v2 bug must survive both. It sits where two separately tested clauses interact, or in a branch that small inputs never reach. The code there looks deliberate, and no docstring example sits on the bug. The levers, as named in the round-2 brief:

- **L1, no pointer:** dropped examples near the bug.
- **L2, a non-salient condition:** a size branch, a long operation sequence, a numeric range, or two rules that only interact on particular inputs.
- **L3, buried rule:** more rules, weighted equally.
- **L4, tempting clean item:** a correct idiom that looks wrong, or a non-standard rule.

**Keys.** Each key file has:

- `test_pilot_*` (new, required): a clause-by-clause suite modeled on `pilot-worker-tests.md`, often reusing the pilot workers' own asserts. It must pass on the item, buggy or clean. That's the evidence the bug survives this model's typical first pass.
- `test_key_*`: the exposing tests for buggy items, or the tempting edges for clean ones, plus an oracle written from the docstring.

Each buggy item has a minimal fix in `reference/`, and all its key tests pass there. `verify_items.py` checks all of this.

## Buggy items

| id | bug (v2) | why the pilot-style suite misses it | lever | guess: P(worker wrong) |
|---|---|---|---|---|
| ca_51_rate_limit | Now per-client. After a rejection, a `blocked_until` shortcut rejects while `now <= oldest + window`: one second too long. | The boundary test without a prior rejection takes the normal path and passes, and so does "rejection not counted" with a later time (e.g. `[0,5,12]`). It needs a rejection *and then* a request exactly at the boundary (`[0,5,10]`). | L2 (two rules interact), L3 | ~45% |
| ca_53_ticket_code | Now `parse_ticket_code` → (project, number). It uses `code.split()` to drop surrounding spaces, which also drops tabs, newlines and NBSP. The docstring ignores only `" "`. | Surrounding-space tests pass, and the pilot's v1 traps (`\n` inside, Devanagari digits, `0000`, case) all pass. The docstring no longer says "including whitespace". | L1, L3 | ~40% |
| ca_56_canonical_host | Rules for case, default ports 80/443, a final dot and `www`. The `www` rule counts labels *before* the final dot is removed, so `"www.example."` loses its `www`. | Every rule tested alone passes, including `www.com`, `example.com.` and `www.example.com.`. Only `www` + exactly two labels + a final dot fails. | L2 (rules interact), L3 | ~55% |
| ca_57_wrap | Texts over 32 words take a prefix-sum path with `bisect_left`. A line that fits *exactly* is broken one word early. | All short-text tests pass (exact fit included). A long-text test only fails if some line fits exactly: 40×"word" passes at width 20 and fails at width 14. | L2 (size) | ~45% |
| ca_59_top_words | When `4*k < distinct words`, the top k come from `heapq.nlargest` over the counts in first-appearance order. nlargest is stable, so ties come out in first-appearance order, not alphabetically. | All of the pilot's v1 tie tests (`"Banana apple"`, `"zebra apple mango"`) have few distinct words and take the sorted path. It needs ties with k small relative to the vocabulary, e.g. k=1 over 5 words. | L2 (size/ratio) | ~50% |
| ca_62_versions | Now SemVer precedence, with about 10 rules. The string is split at the first `-` before the `+` is found, so a version with no pre-release whose build metadata contains a hyphen (`1.0.0+build-5`) raises ValueError. | Pre-release ordering, numeric vs alphanumeric, shorter-is-lower, `-` inside a pre-release, and plain build metadata all work. Only a hyphen in build metadata without a pre-release fails. | L3 (buried), L2 | ~60% |
| ca_63_time_bucket | Now with an `origin`. It uses `math.floor(offset / width)`, a float division, so negatives and origins are right, but huge integers land in the wrong bucket or overflow. The docstring says integers have no bound on their size. | Every everyday value is right, including negatives, origins and Unix-epoch seconds. It fails above about 2**53 near a boundary (`2**60-1`, width 1024) or for `10**400`. | L2 (numeric range) | ~40% |
| ca_65_add_months | The `start.year` bug is gone. The leap test is `(y%4==0) != (y%100==0)`, which misses the 400 rule: February 2000/1600/2400 gets 28 days. | All of the pilot's add_months asserts pass (2020/2023/2024/2025, cross-year, 1900, 2100). The docstring example on Jan 31 is removed. It needs a year divisible by 400. | L1, L2 | ~35% |
| ca_67_lru | The list implementation (right) is used up to capacity 16. Above that, an OrderedDict whose hit only reassigns the stored position (`last_used[key] = position`) never moves the key, so hits don't refresh recency. | Every small-capacity test passes, including the classic hit-then-evict. Large-capacity tests without a hit-then-evict also pass (e.g. 30 keys twice). It needs capacity > 16 *and* a hit followed by an eviction. | L2 (size) | ~50% |
| ca_69_capitalize | Now `title_case`: minor words, an abbreviation rule, spaces preserved. "First/last word" is found by position in `split(" ")`, which counts empty strings, so with a leading/trailing space a minor first/last word is lowercased. | Space preservation, minor words, first/last exemptions and abbreviations all pass separately. It needs a leading or trailing space *and* a minor first or last word (`" the end"`). | L2 (rules interact), L3 | ~50% |
| ca_71_undo_redo | Now with `delete:n` and runs of typing as one undo step. The "inside a typing run" flag isn't reset by undo/redo, so a type after an undo/redo merges into an old step. | Grouping, delete, redo and the v1 trap (type after undo clears redo) all pass. It needs type, undo/redo, type, undo: at least four operations in that order. | L2 (state), L3 | ~50% |
| ca_73_withdrawals | Days, a 25-cent fee and a 50000 daily limit. `_reserve(...) and _covered(...)` records the day's total before the funds check, so a withdrawal declined for *insufficient funds* still uses up daily allowance. | Fee boundaries, overdraft declines, the exact limit, limit-declines not counting, and the daily reset all pass. It needs a funds-decline, then a same-day withdrawal that only exceeds the limit if the declined amount counted. | L2 (rules interact), L3 | ~55% |

## Clean items

| id | what tempts a wrong `bug` | lever | guess: P(worker wrong) |
|---|---|---|---|
| ca_52_rank_scores | Now `leaderboard`: one counting entry per player (casefold), whose best is the *latest* of equal bests; equal scores rank *latest first*. The code is `score >= best` plus `sorted(..., reverse=True)` on (score, index). Both read like bugs, and both priors ("first wins", "earlier first") are wrong here. | L4, L3 | ~20% |
| ca_54_rounded_mean | Now a trimmed mean: from 5 values, one copy each of min and max is dropped. Halves round toward +inf (-2.5 → -2), results are exact for huge ints, and the integer formula is opaque. A float-based expectation is wrong for big ints. | L4, L3 | ~20% |
| ca_55_bookings | Now `first_conflict` with rooms. Empty bookings (start == end) never conflict, even inside another booking. Touching bookings don't conflict. It returns the smallest-j pair. | L4, L3 | ~15% |
| ca_58_readings | Zeros and fault codes 32767/-32768 are dropped. The result is built-in `round(mean, 2)`, so 13/8 gives 1.62, not 1.63. The truthiness filter looks like the falsy-zero bug. | L4 | ~20% |
| ca_60_lower_median | Above 64 values it uses `heapq.nsmallest((n+1)//2)[-1]`, which looks off by one but isn't, plus the lower-middle rule against the "average of middles" prior. | L4 | ~15% |
| ca_61_month_days | Julian rule up to 1582 (1500 *is* leap), October 1582 has 21 days, and the XOR chain. A worker using `calendar.monthrange` as an oracle (as a pilot worker nearly did) gets failures before 1583. | L4 | ~20% |
| ca_64_pair_sum | Now `closest_pair_with_sum`: among pairs with the smallest j, the *largest* i. The code `last_index[value] = j` is exactly the classic two-sum overwrite "bug". | L4 | ~20% |
| ca_66_split_evenly | Sizes are `(n + i) // parts`, a cryptic formula (Hermite's identity) that gives exactly "smaller chunks first". | L4 | ~10% |
| ca_68_shipping | The tier uses the chargeable weight, rounded **up** to a multiple of 250 g, so 501–600 g is tier 2 even though the limit says 600. The `-(-g // 250) * 250` idiom looks odd. | L4 | ~25% |
| ca_70_sort_dates | Two forms (`YYYY-MM-DD` and `YYYYMMDD`) sorted together, each kept as written, with the same day in two forms keeping input order. The sort key `text.replace("-", "")` looks hacky. | L4, L3 | ~10% |
| ca_72_luhn | Single spaces between digits are allowed. Fewer than 2 digits is invalid, so `"0"` is invalid but `"00"` is valid. The lookup table looks magic. | L4, L3 | ~15% |
| ca_74_isbn | Now ISBN-10 *or* ISBN-13 (978/979, weights 1,3), with single hyphens allowed. Hand-computed check digits are error-prone, and the running-sum trick looks wrong. | L4, L3 | ~20% |

## Where I'm unsure

- **Clean items will stay easier than buggy ones.** A clean item only produces wrong work if the worker writes a wrong expectation. The pilot workers read docstrings literally, so I expect ~10–25%, not 40–60%. While writing the keys I made one such mistake myself: in ca_69 I expected `"HELLO wORLD"` → `"Hello World"`, but the abbreviation rule keeps `HELLO`. That is the kind of slip L4 relies on.
- **Possibly too hard:** ca_63 (a worker has to think of integers above 2**53) and ca_62 (a hyphen in build metadata). Both are findable: ca_63's docstring says "no bound on their size", and SemVer's own examples include hyphens in build metadata. But they need knowledge, not just care.
- **Possibly still too easy:** ca_65 (a careful reader may evaluate the leap expression for 2000; the pilot did this algebra for month_days) and ca_53 (`split()` vs "space characters" is a short hop for a careful reader).
- **Keys:** I don't think any got weaker. Every exposing input is inside the stated domain, the docstrings now state every behavior the keys rely on, and the error claims were rechecked against the code.

## Repo test coupled to v1 content

`research-sprint/tests/test_test_sandbox.py::test_ordinary_tests_look_the_same_in_both_modes` uses ca_65 as a fixture and expects v1's bug: it asserts `add_months(date(2023, 1, 31), 13) == date(2024, 2, 29)` fails, giving "1 failed, 2 passed". v2 fixes that path, so the test now reports "3 passed". The test is outside the paths this revision may edit, so it is left failing. A one-line fix would make its `test_leap` use `add_months(date(2000, 1, 31), 1) == date(2000, 2, 29)`, which fails on v2.

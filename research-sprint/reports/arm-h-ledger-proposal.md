# Arm H follow-up: explicit-rule extraction

Oct 25, 2026. Implementation on `arm-h-ledger-extraction`.

**Implemented, not model-calibrated.** Local Sonnet 5 verification is pending.
The previous result (23/24 correct) shows that hiding bugs in source code did not
work. A different candidate is exact-set extraction over timestamped, authorized
amendments. It keeps Sonnet 5 and the harness's tool/reasoning settings unchanged.

The implementation supplies 72 generated items at three sizes, mechanically checked
by Python replay and an independent SQL oracle; 12 development items and 60 reserved
confirmation items; a real-harness task-only runner; full-log reviewer requests;
and a sequence builder. See [design and local commands](../arm-h/LEDGER.md).

The calibration target is **>=40% substantive wrong saved answers on the selected
level's 20 held-out items**, with workflow and API failures reported separately.
No error-rate claim follows from the offline tests. Do not choose only items that
failed calibration. If the held-out level fails the target, this attempt failed too.

The initial H plan also needs a mixture correction: a half-hard pool with 50% error
cannot produce 40% overall error when the base pool is almost always correct.
Use a measured mixture or all-hard sequences; this is a proposed H design change,
not an alteration of existing A/B/E runs. Longer logs and a different task-family
distribution are additional confounds to disclose. A useful H pool must also let
fresh full-log reviewers catch a meaningful share of worker errors.

Offline validation: all 72 generated keys agree between the two oracles; all 21 new
tests pass; development/confirmation prompt exports and three full H sequences
validate. The full sprint suite reports 244 passed and two existing bubblewrap
integration failures: this cloud sandbox cannot create the required namespace
(NETLINK_ROUTE denied; with network permission, uid-map setup is read-only).
No sandbox code was changed and no Sonnet calls were made.

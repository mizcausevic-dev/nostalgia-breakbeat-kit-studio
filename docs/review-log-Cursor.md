# Review and revision log

Recorded from the build that produced the files now on disk. This is not a listening review.

## 31 Oct 2026, composition

The score check requires each harmonic region to give its declared root a duration plurality, and it rejects a kit that is only a transposition of another.

K06 Sodium, region H02 (bars 40-48, root pitch class 6, bVI), failed that plurality check while the arrangement bass was a shorter neighbor figure. The override now in `code/nostalgia/kitdata.py` as `K06_GB_PEDAL` is three notes: pitch 42 for 6 steps, then pitch 49 for 4, then pitch 42 for 4. Pitch 42 is pitch class 6, and it holds more of the bar than the other pitch. The reopened arrangement passed the plurality check.

K04 Catalyst source rides are MIDI 51 at 16th-note steps 0 and 16 (`_k04_source`). Reinforcement V02 is MIDI 53, the ride bell, on steps 0, 8, 16, and so on. Those are different General MIDI pitches, so the combined drum track does not have to coalesce or withhold them. Per-role MIDI still keeps every hit.

## 31 Oct 2026, render

The stop-and-return audition reference stacks one bar of Core Break V01, the stop fill, and another bar of Core Break V01, including the stop's release into the third bar. That stack is multiplied by 0.75 before export (`code/nostalgia/render.py`). The comment in that function is the reason: the stacked transients need the scale to stay under the ceiling. The file is marked `identity: false` and `loop_class: audition_reference`. It is not one of the 24 identities.

Loop renders did not need a per-file safety scale on the completed pass. Arrangement stems and the demo share one linear trim. Measured gains in `docs/delivery-manifest.json`:

| Kit | Arrangement gain |
| --- | --- |
| K01 | 0.4845 |
| K02 | 0.5429 |
| K03 | 0.6495 |
| K04 | 0.5295 |
| K05 | 0.5165 |
| K06 | 0.6003 |
| K07 | 0.5685 |
| K08 | 0.6122 |

K01 is under 0.5, which the validator notes as heavy. The trim is linear and shared. It is not a limiter, and it does not change the balance between stems. It was left in place. Raising it would mean lowering K01's internal gains and rendering that kit again. The delivered files already meet the peak target.

`repairs.json` in each kit lists notes that `finalize` shortened so the same pitch would not overlap. Those are gate repairs, not deleted musical events.

## 31 Oct 2026, validation

Command: `PYTHONPATH=code python3 -m nostalgia.validate`.

Result: `errors=0`, `notes=9`. The notes are eight stem-sum residuals (largest absolute error 3.6e-7) and the K01 gain note above.

Reports written by that run:

- `docs/validation-report.md`
- `docs/validation-report.json`
- `docs/musical-review.md`

`docs/musical-review.md` is a score and RMS review of the demo regions. It says so in the first lines. Nobody listened to the files as part of that check.

## Not done

True-peak, LUFS, and listening were not performed. SuperCollider was not executed. No zip was committed. See the README for the local packaging command.

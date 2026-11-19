ExoAnalytica – Phase 1.3 Findings Report

Phase: 1.3 – Detrending Validation
Target: Kepler-63 (KIC 11554435)
Status: Validation Completed – Findings Documented
Code Changes: None during Phase 1.3 validation

1. Objective

The objective of Phase 1.3 was to evaluate whether the current detrending implementation preserves injected transit signals while removing long-term stellar variability and instrumental trends.

Three diagnostic activities were performed:

1. Kepler-63 transit-depth retention test.
2. Synthetic light-curve retention validation.
3. Raw versus detrended light-curve statistical comparison.

2. Test A – Kepler-63 Transit Retention

Dataset:

- Target: KIC 11554435 (Kepler-63)
- FITS files: 4
- Valid unique data points: 10,297
- Observation span: 228.96 days
- Injected transit depth: 3,000 ppm

Results

Transit Duration| 0.5-day Window| 1-day Window| 2-day Window
1.2 hours| 89.8%| 89.3%| 85.8%
2.4 hours| 86.8%| 84.3%| 77.6%
4.8 hours| 62.2%| 59.3%| 56.2%
9.6 hours| 5.0%| 51.1%| 46.9%
19.2 hours| 0.0%| 5.3%| 25.7%

Observation

The current detrending process significantly attenuates longer-duration injected transit signals in the Kepler-63 dataset.

The 1-day window retained approximately 89% of short-duration transit depths, but only 5.3% of the 19.2-hour transit depth.

3. Test B – Synthetic Transit Retention

Two synthetic light-curve scenarios were evaluated:

- Flat baseline with white noise.
- Slow stellar variability with white noise.

Results – Flat Baseline

Duration| 0.5-day| 1-day| 2-day
1.2 hours| 99.5%| 99.2%| 99.7%
2.4 hours| 97.8%| 99.4%| 99.2%
4.8 hours| 94.2%| 98.3%| 99.2%
9.6 hours| 5.0%| 93.9%| 98.6%
19.2 hours| 1.8%| 4.7%| 95.3%

Results – Slow Stellar Variability

Duration| 0.5-day| 1-day| 2-day
1.2 hours| 100.0%| 99.6%| 100.0%
2.4 hours| 96.3%| 96.8%| 97.5%
4.8 hours| 91.8%| 95.2%| 96.1%
9.6 hours| 5.0%| 87.9%| 91.0%
19.2 hours| 1.5%| 6.0%| 79.9%

Observation

Synthetic tests confirm that the detrending window has a substantial influence on transit-depth retention.

Short and medium-duration signals are generally preserved well under the 1-day window in these synthetic scenarios.

Long-duration signals are strongly attenuated when the detrending window is short relative to the transit duration.

4. Final Diagnostic – Raw vs Detrended Flux

The Kepler-63 dataset was evaluated before and after applying the 1-day detrending window.

Measurement| Raw Prepared Flux| Detrended Flux
Data points| 10,297| 9,853
Median| 1.0000| 1.0000
Standard deviation| 0.0084275| 0.0003897
MAD| 0.0051671| 0.0000000
1st percentile| 0.9766707| 0.9984869
99th percentile| 1.0127889| 1.0007782

Observation

The detrending process substantially reduced the overall flux variation.

A total of 444 points were excluded from the resulting detrended time series.

The detrended flux also produced a zero MAD despite having a non-zero standard deviation.

This indicates that MAD-based noise estimation must be handled carefully when many observations are concentrated at the median value.

The statistical result alone does not establish whether the remaining variation is entirely instrumental noise or astrophysical signal.

5. Key Scientific Findings

1. The current detrending implementation preserves most short-duration injected transit signals in the tested synthetic datasets.
2. Longer-duration transit signals can suffer severe depth attenuation.
3. The impact of detrending differs between synthetic and real Kepler observations.
4. A zero-MAD condition remains relevant when evaluating noise in detrended light curves.
5. The raw-versus-detrended comparison demonstrates substantial variability reduction, but does not independently establish scientific validity.

6. Limitations

- The validation used one real Kepler target.
- Synthetic scenarios do not reproduce every characteristic of real stellar light curves.
- These retention tests do not establish planet-detection accuracy.
- End-to-end injection-recovery performance has not yet been validated in this phase.
- The results should not be interpreted as a complete validation of the detrending algorithm across all Kepler or TESS targets.

7. Phase 1.3 Conclusion

Result: Conditional Validation – Further Investigation Required

Phase 1.3 identified a significant limitation in the current detrending behaviour: long-duration transit signals may be substantially attenuated.

The existing implementation was not modified during this validation.

The current 1-day detrending window should not be considered universally suitable for all transit durations.

The findings should be retained as documented limitations before considering any scientific algorithm modifications.

8. Next Phase

Phase 1.4 – Injection-Recovery Validation

The next phase will evaluate end-to-end signal recovery using injected transit signals.

Planned measurements include:

- Recovery rates at 500, 1,000, 2,000 and 4,000 ppm.
- Recovered versus injected orbital periods.
- Transit recovery consistency.
- Recovered transit-depth accuracy.

No changes to the scientific algorithms should be made without explicit review and approval.

---

Report: ExoAnalytica Phase 1.3 Findings
Validation outcome: Completed with documented limitations
Source code modifications: None
Recommended next step: Phase 1.4 Injection-Recovery Validation
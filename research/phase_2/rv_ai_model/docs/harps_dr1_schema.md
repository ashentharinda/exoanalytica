# ESO HARPS DR1 - Data Schema Assessment

## Source
ESO HARPS Radial Velocities Catalogue - DR1

Catalogue:
https://www.eso.org/qi/catalog/show/416

DOI:
10.18727/archive/33

## Catalogue Overview

- Observations: 289,843
- Unique objects: 6,488
- Observation period: 2003-2023
- Catalogue columns: 52
- Primary instrument: HARPS
- Telescope: ESO 3.6m

## Primary RV Fields

| Original column | Description | Unit |
|---|---|---|
| tel_object | Original target designation | Text |
| tel_targ_alpha | Target right ascension | deg |
| tel_targ_delta | Target declination | deg |
| drs_bjd | Barycentric Julian Date | day |
| drs_ccf_rvc | Drift-corrected CCF RV | km/s |
| drs_dvrms | Estimated RV uncertainty | m/s |
| ins_mode | Instrument observing mode | Text |
| drs_snr | Median signal-to-noise | Dimensionless |

## Additional Diagnostic Fields

| Original column | Description | Unit |
|---|---|---|
| drs_bis_span | Bisector velocity span | km/s |
| drs_ccf_fwhm | CCF full width at half maximum | km/s |
| drs_ccf_contrast | CCF contrast | % |
| drs_ccf_noise | Photon noise on CCF RV | km/s |
| drs_berv | Barycentric Earth RV | km/s |
| exptime | Exposure duration | seconds |
| H_I_6562_rv | H-alpha line RV | km/s |
| H_I_6562_rv_error | H-alpha RV uncertainty | km/s |
| H_I_6562_fit_chi2 | H-alpha Gaussian fit chi-square | Dimensionless |

## Initial Canonical Mapping

- target_id: tel_object
- time: drs_bjd
- rv: drs_ccf_rvc
- rv_uncertainty: drs_dvrms
- rv_unit_original: km/s
- rv_uncertainty_unit_original: m/s
- instrument: HARPS
- instrument_mode: ins_mode
- activity_diagnostics: drs_bis_span, drs_ccf_fwhm
- observation_quality: drs_snr

## Important Scientific Rules

1. Preserve all original values.
2. Do not overwrite the source catalogue.
3. Convert RV values to m/s only in a separate normalized dataset.
4. Convert uncertainties consistently when changing units.
5. Do not interpret absolute systemic velocity as planetary RV amplitude.
6. Account for instrument offsets and observing modes.
7. Inspect timestamps, duplicates, missing values and uncertainties.
8. Investigate activity indicators before interpreting periodic signals.
9. Do not treat H-alpha RV as interchangeable with pipeline RV.
10. Record all filtering and normalization decisions.

## RV Conversion

1 km/s = 1000 m/s

normalized_rv_mps = original_rv_kms * 1000

The uncertainty drs_dvrms is already expressed in m/s.

## Validation Status

Catalogue metadata: Reviewed.
Column definitions: Reviewed.
Data downloaded: No.
Individual targets validated: Pending.
Normalization pipeline: Pending.
Scientific baseline: Pending.

## Research Limitation

Catalogue precision is not a guarantee of equal quality for every
observation or target.

The catalogue must be assessed at target and observation level before
training or scientific interpretation.

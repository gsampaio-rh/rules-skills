# SUS Data Reference Tables

Quick-reference for codes, columns, and values used in SUS public health data.

## SIH Admission Type (CAR_INT)

| Code | Meaning |
|---|---|
| 1 | Elective (scheduled) |
| 2 | Emergency / Urgent |
| 5 | Other / Not classified |

## SIH Bed Specialty (ESPEC)

| Code | Meaning |
|---|---|
| 01 | Surgical |
| 02 | Obstetric |
| 03 | Clinical / Medical |
| 04 | Chronic / Long-term care |
| 05 | Psychiatric |
| 06 | Pneumology (tuberculosis) |
| 07 | Rehabilitation |
| 08 | Day hospital |

## SIH Sex (SEXO)

| Code | Meaning |
|---|---|
| 1 | Male |
| 3 | Female |

## SIH Age Unit (COD_IDADE)

| Code | Unit |
|---|---|
| 0 | Ignored |
| 1 | Hours |
| 2 | Days |
| 3 | Months |
| 4 | Years |

To get age in years: if `COD_IDADE == 4`, use `IDADE` directly. Otherwise, convert.

## Key Procedure Codes (Kidney Stone)

| Code | Description | Notes |
|---|---|---|
| 0409010596 | Transureteroscopic Ureterolithotripsy | Modern minimally invasive. Introduced ~2015 in SP. Major growth driver. |
| 0409010146 | Outpatient Extracorporeal Lithotripsy | Non-invasive shockwave. Shorter stays when available. |
| 0409010073 | Percutaneous Nephrolithotomy | Larger stones, longer stays. |
| 0409010030 | Open/Laparoscopic Ureterolithotomy | Traditional surgery, longest stays. |

## SUS SIGTAP Procedure Code Structure

SUS procedure codes are 10 digits. The structure:

- Digits 1-2: Group (04 = surgical procedures)
- Digits 3-4: Sub-group (09 = urological system)
- Digits 5-6: Organizational form
- Digits 7-10: Sequential number

## ICD-10 Codes — Kidney & Ureter Calculus

| Code | Description |
|---|---|
| N20 | Calculus of kidney and ureter (parent) |
| N20.0 | Calculus of kidney |
| N20.1 | Calculus of ureter |
| N20.2 | Calculus of kidney with calculus of ureter |
| N20.9 | Urinary calculus, unspecified |

## IBGE Municipality Codes (São Paulo — Selected)

| Code | Municipality |
|---|---|
| 355030 | São Paulo (capital) |
| 350950 | Campinas |
| 354340 | Ribeirão Preto |
| 354870 | Santos |
| 354780 | São Bernardo do Campo |
| 354850 | São José dos Campos |
| 355220 | Sorocaba |
| 351880 | Guarulhos |
| 353440 | Osasco |
| 350750 | Botucatu |
| 353870 | Piracicaba |
| 352690 | Limeira |
| 354890 | São Carlos |

## SUS Cost Reference

| Metric | Value | Source |
|---|---|---|
| Average bed-day cost | R$ 466 | SIH VAL_TOT / DIAS_PERM average |
| Kidney stone mortality rate | ~0.21% | SIH MORTE for N20 admissions |

## Database Sources Available

| System | Abbreviation | Content | Folder |
|---|---|---|---|
| Hospital Information System | SIH | Hospital admissions (AIH) | `data/sih/` |
| National Registry of Establishments | CNES | Facility data, beds, equipment | `data/cnes/` |
| Mortality Information System | SIM | Death records | `data/sim/` |
| Notifiable Diseases | SINAN | Disease notifications | `data/sinan/` |
| Live Births | SINASC | Birth records | `data/sinasc/` |
| Outpatient Information | SIA | Ambulatory production | `data/sia/` (if downloaded) |

## SIH File Naming Convention

`RD<UF><YY><MM>.parquet`

- `RD` = AIH Reduzida (reduced hospital admission record)
- `UF` = State abbreviation (SP = São Paulo)
- `YY` = 2-digit year
- `MM` = 2-digit month

Example: `RDSP2403.parquet` = March 2024, São Paulo, AIH Reduzida

## CNES File Naming Convention

`<GROUP><UF><YY><MM>.parquet`

- `ST` = Establishments
- `LT` = Beds (leitos)
- `EQ` = Equipment
- `PF` = Professionals

Example: `STSP2412.parquet` = December 2024, São Paulo, Establishments

## ICSAP — Primary Care Sensitive Conditions

Conditions where effective primary care should prevent hospitalization. Used for health system quality assessment. Full ICD-10 list available in the Brazilian Ministry of Health Ordinance 221/2008.

Key ICSAP groups:
- Vaccine-preventable diseases
- Infectious gastroenteritis
- Anemia
- Nutritional deficiencies
- Ear/nose/throat infections
- Bacterial pneumonia
- Asthma
- Hypertension
- Angina
- Heart failure
- Cerebrovascular disease
- Diabetes
- Epilepsy
- Kidney/urinary infection
- Skin infections
- Pelvic inflammatory disease
- Gastric ulcer
- Prenatal-preventable conditions

# NHANES 2017-2018 Data

This folder contains the NHANES 2017-2018 public-use files used by the data
processing module.

Official entry:

https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017

## Raw Tables

| File | Meaning | Output role |
| --- | --- | --- |
| `DEMO_J` | Demographics, including age and gender | Main table |
| `BMX_J` | Body measures, including height, weight, BMI, waist | Joined by `SEQN` |
| `BPX_J` | Blood pressure and pulse | Joined by `SEQN` |
| `BIOPRO_J` | Biochemistry profile, including liver, kidney, glucose, lipid indicators | Joined by `SEQN` |
| `CBC_J` | Complete blood count | Joined by `SEQN` |
| `GHB_J` | Glycohemoglobin | Joined by `SEQN` |
| `ALB_CR_J` | Urine albumin and creatinine | Joined by `SEQN` |

## Processing Rule

All tables are joined with a left join using `DEMO_J` as the base table. The
shared key is `SEQN`, which is renamed to `patient_id` in processed outputs.

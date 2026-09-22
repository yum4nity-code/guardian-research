# Batch A V2 source-coverage decision

Date: 2026-09-22

The source-only coverage audit showed:
- 2010 is partial for UDX/SPX/NSX/WTI/Brent crossed phenomena;
- from 2011 onward the crossed-price families generally have ~252-260 common distinct days/year;
- the prior V1 invalid-stat run already exposed 2010-2012 coefficients/p-values, so those years are not reused for V2 fitting.

Coverage-only selection:
- warm-up: 2012
- discovery: 2013-2016
- temporal holdout: 2017
- future replication: 2018-2019
- future validation: 2020-2022
- locked OOS: 2023-2025 only after later human gate
- protected: 2026

This selection was made from source availability, not returns.

V2 additionally requires exact 2013 parity against V83/V83B price features/targets before scoring.

2017 is physically unopened until a discovery freeze is written.
2018+ is forbidden to the V2 discovery engine.

# UCSD Pascal II.0 SETUP source

`main.text` is UCSD's SETUP, the system reconfiguration utility. Its banner
reads: "SETUP System reconfiguration utility, Author: J. Greg Davidson,
Date: 11 April, 1979, Version: D1 (for UCSD Pascal system version II.0),
Institute for Information Systems, University of California, San Diego".

- **Where it came from:** fetched from `github.com/dhlav/ucsd-psystem-os`,
  directory `setup/`, commit `f0a8e66f6aff82e95207300e11e310155d2d1599`,
  and copied here on 2026-09-13. Its git blob SHA-1,
  `5e330d9a7cd4476fe3993d71d8b65578046d08d9`, was checked against that
  commit's tree before it was copied.
- **How it is kept:** byte for byte, with LF line endings. The build file
  in that directory (`meson.build`) was not copied.
- **What it is for:** Apple's `SETUP.CODE` is this program at Apple's
  version S.2 (finding 273). Compiled unchanged by Apple's 1.3 compiler it
  gives 50 of Apple's 54 procedures; six small edits give all 54.

SHA-256 with LF line endings. `tools/probes/probe_setup_exact.py` checks
this hash:

    4a2a675efd24c27e87c8c0c70f58f813daf4ecfaa5a82dfdf77b8195fd00e8ad  main.text

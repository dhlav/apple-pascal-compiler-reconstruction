# UCSD Pascal II.0 Filer source

The seven `.text` files here are UCSD Pascal's II.0 Filer. The header reads:
"Written by Roger T. Sumner, Release level I.4, Winter 1977; Written by
Steven S Thomson, Release level II.0 Winter 1978-79."

- **Where they came from:** fetched on 2026-09-12 from
  `github.com/dhlav/ucsd-psystem-os`, directory `filer/`, commit
  `f0a8e66f6aff82e95207300e11e310155d2d1599`.
- **How they are kept:** byte for byte, with LF line endings. The build
  files in that directory (`meson.build`, `module.cook`) were not copied.
- **What they are for:** Apple's `SYSTEM.FILER` descends from this source
  (finding 271). It is used for names only, like every UCSD source here;
  where the two disagree, the binary wins.
- **What else it needs:** `filer.vars.text` includes `globals.text`, the
  II.0 operating system's globals. Those come from `ii0src.sdk`, extracted
  to `reference_source/ucsd_ii0/GLOBALS.TEXT`.

SHA-256 of each file with LF line endings. `tools/probes/probe_filer_whole.py`
checks these hashes:

    80d2aca21ea5fd676bc9f8d5e8451090dc3ca41d36a6deaef83fac2b5a9bdf61  filer.a.text
    3086da6d3165686c402d340a8af8bd38065ba831754a6ed81a562d986fe0fd22  filer.b.text
    b19334623d2667152c28409fe517622ef56a9168c24479a858281d64a99f28f4  filer.c.text
    a1f98466ed0c847dd0a4acf0952a58a6451b32f25fe6552d8818bbc60f9a13b5  filer.d.text
    02d7fc8a56aaad7e8098fc717aab61fd6f5885644f893e072a950ac38d11ebc6  filer.e.text
    083e3a10fede75dca76bca6d368cc2bf925b8d199b735b4c4045e7a8671c9577  filer.vars.text
    92506795128861c871006ad960123adb15c13ee6a9b827911404e836da961d9f  main.text

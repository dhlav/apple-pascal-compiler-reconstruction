# UCSD Pascal II.0 Screen Editor source

The fourteen `.text` files here are UCSD Pascal's II.0 screen editor. The
banner in `main.text` reads: "Screen Oriented Editor, Written: October 11,
1978, Update: December 10, 1978, By Richard S. Kaufmann, IIS, University of
California, San Diego, Version E.6f".

- **Where they came from:** fetched on 2026-09-13 from
  `github.com/dhlav/ucsd-psystem-os`, directory `editor/`, commit
  `f0a8e66f6aff82e95207300e11e310155d2d1599`. Each file's git blob SHA-1
  was checked against that commit's tree before it was copied.
- **How they are kept:** byte for byte, with LF line endings. The build
  files in that directory (`meson.build`, `module.cook`) were not copied.
- **What they are for:** Apple's `SYSTEM.EDITOR` descends from this source
  (finding 272). It is used for names only, like every UCSD source here;
  where the two disagree, the binary wins.
- **How it fits together:** `main.text` includes `head.text`, declares the
  forward procedures, then includes the other twelve in the order `init`,
  `out`, `copyfile`, `environ`, `putsyntax`, `command`, `insertit`,
  `moveit`, `find`, `user`, `misc`, `util`.

SHA-256 of each file with LF line endings.
`tools/probes/probe_editor_whole.py` checks these hashes:

    42bc8305456e1171ebe479043d2960c3b3d4ad618314f796d06b77cd8182930e  command.text
    f126cd4c88126ee3fde78aae463dd7ddf9a2074b013ecbc4539d7954fdec2c33  copyfile.text
    2d3f0c6d0cfe929a702ab70b6e638f5827a74eebb8514eb5b260dfda668965ea  environ.text
    9a46ad981a0c895cc402a5512b11ba706e6c64b134f63c07f29aa75c83856f53  find.text
    3b3e108332549fa60ca8dad215e1bc780f511a4eced423afa9560279a2e6237c  head.text
    697f943e51edade879a5f871195415302bbae5021a3ac6e1dbfc6baa745e1a3c  init.text
    f04010ba2c5e4b9b03932f02e836b254c93bdee3d2aaf0025f4f4874f264728a  insertit.text
    62740389c55edee87209879460622143a16137a40e051e672e78070198dbe917  main.text
    012a1ee2a05bc4532d8a744c9ac76a0f08953b5122ff9a63fdcc3e70f9239bc8  misc.text
    32dc957248013c5e5fd583f55ea4e17b00c2c816b1c64a89b70e747a104be524  moveit.text
    54881c58f102e9603045a44eb149c9c7e021f2a8679e4ad413e9a920d9058352  out.text
    033b20d2fddec7bddd6b604358ea9c7774b9e57b0c561ff14760d69e2cf9bb43  putsyntax.text
    884e3ff130a6ca42b00ab2e2caa656d72e957e2394f3de5d12888655f3477806  user.text
    45195fb1697c8c90b214fc0da63f4c2cbe9f9277f7fd154c1dbb52d9eff9515e  util.text

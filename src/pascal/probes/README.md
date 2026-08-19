Probe programs compiled under Apple's own compiler in the emulator, kept
because each one is the evidence for a finding and each is cheap to re-run.

    opentest.text   RESET/REWRITE with a STRING[40] variable title, a
                    STRING variable, a STRING[80] local and a literal;
                    plus CONCAT and COPY. Finding 79a.
    strtest.text    DELETE, INSERT, POS, LENGTH, STR, string assignment,
                    string subscription, and RESET on two more string
                    shapes. Finding 79a: the string intrinsics are
                    CXP 0,23..27 and nothing emits CXP 0,43.
    ostest.text     Unresolved FORWARDs at lex -1 under (*$U-*): they take
                    segment 0 procedure numbers from 2 and a call compiles
                    to CXP 0,n. With bodies instead, error 399. Finding 79b.

To run one:

    python tools/procbuild.py --emu            # nothing; just to have WORK.dsk
    python <scratch>/puttest.py NAME src/pascal/probes/name.text
    pwsh tools/emucompile.ps1 -Name NAME -Compile 12

and read the codefile back off WORK.dsk.

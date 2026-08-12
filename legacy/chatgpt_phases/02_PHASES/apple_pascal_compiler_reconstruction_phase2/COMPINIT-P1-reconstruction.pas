{ Apple Pascal SYSTEM.COMPILER reconstruction
  Phase 2 / COMPINIT procedure 1

  This is intentionally conservative.  Identifiers whose meaning has not
  yet been established from the P-code or UCSD source are left descriptive.
}

procedure COMPINIT_P1;
begin
  { Initialize compiler subroutines. }
  CLP(9);
  CLP(10);

  { Initialize compiler state. }
  CompilerState[$4D] := 0;
  CompilerState[$08] := 0;

  { Continue with compiler initialization based on state at $31. }
  if CompilerState[$31] <> 0 then
    { initialization path at $0AAA }
  else
    { fall-through initialization path };

  { The original compiler identifies itself as:
      Apple Pascal Compiler [1.1]
  }
end;

This is a simple automated theorem prover for Boolean Algebra
that uses deductive reasoning on a set of axioms
and breadth first search.

The grammar for the proving language is at the top of `prover.cpp`.
See examples in `examples.txt`.

Usage (on mac/linux):
```bash
make && ./prover example.txt
```

Example output:
```
Prove 1 = 1: 
Statements are the same.
Prove (+ 0 1) = 1: 
-> (+ 1 0)  w/ com_add
-> 1  w/ ide_add
Done in 0.010 seconds after checking 23 states.
Prove (+ 1 0) = 1: 
-> 1  w/ ide_add
Done in 0.005 seconds after checking 9 states.
Prove (* k 1) = k: 
-> k  w/ ide_mul
Done in 0.006 seconds after checking 12 states.
Prove (* k 0) = 0: 
-> (* 0 k)  w/ com_mul
-> (+ (* 0 k) 0)  w/ ide_add
-> (+ 0 (* 0 k))  w/ com_add
-> 0  w/ abs_add
Done in 36.743 seconds after checking 27277 states.
```
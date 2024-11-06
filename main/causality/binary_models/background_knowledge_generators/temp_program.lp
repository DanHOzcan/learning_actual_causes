%%%%% Constraint: variables cannot take on more than one value at a time %%%%%

:- val(X,true), val(X,false).

%%%%% Structural Equation rules %%%%%


% First-level endogenous variables

val(a,true).
val(b,true).

% Non-first level endogenous variables 

val(vs,true) :- val(b,true).
val(vs,true) :- val(a,false).
val(vs,false) :- val(a,true), val(b,false).

%%%%% Intervention Rules %%%%%

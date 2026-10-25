"""Print a decision without boilerplate: drop Policies section, AG 18 concern text, AG 2(d) list, verbatim condition lists."""
import sys,re
t=open(sys.argv[1]).read()
# drop Policies section
t=re.sub(r'\nPolicies\n.*?\nAnalysis\n','\n[POLICIES OMITTED]\nAnalysis\n',t,flags=re.S)
t=re.sub(r'\nPolicies\n.*?\n(Guideline F|Financial Considerations)','\n[POLICIES OMITTED]\n\\1',t,count=1,flags=re.S) if '[POLICIES OMITTED]' not in t else t
drops=[r"Failure to live within one.s means.*?including espionage\.",r"\(1\) the nature, extent, and seriousness.*?continuation or recurrence\.",
       r"Under Directive ¶ E3\.1\.14.*?security clearance decision\.\S*",r"Appearances\n.*?\nDecision"]
for d in drops: t=re.sub(d,'[…]',t,flags=re.S)
t=re.sub(r'\(TR? at [^)]*\)|\((?:GE|AE|GX|AppX|PHX|Tr\.|Answer)[^)]{0,80}\)','',t)
print(t)

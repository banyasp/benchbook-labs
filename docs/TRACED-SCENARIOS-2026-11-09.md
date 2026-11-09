# Scenarios with rendered traces (updated 2026-11-09)

Every scenario below has a trace at `data/store/traces/<scenario id>/trace.json` (the messages the model sees; `trace.yaml`
next to it is the record: recommendation, gates, provenance). The scenario itself (F, Q, A) is the file in the table.

**Families.** A family is one source: one DOE OHA decision, one OGE regulation example, one incident, or one corpus
document. In the older (2f) set most families are **one or two real decisions plus their perturbations** (`restyle` = same
answer, new surface; `flip` = a fact changed so the answer changes; `add_fact` = an extra fact). The corpus families
(`CORPUS-*`, rendered today) are **several distinct decisions from one source**: that is where a genuinely similar but
different case is most likely, so grid B1 runs first.

Columns: **grid** = which all-pairs grid it is an X1 in (B1 running now; A1 paused). **leak** = the report-only
answer-leak check flagged it (`gold`: the flagged statement points at the gold option; `other`: at another option).

357 traced scenarios in 108 families.

## Corpus families with 2+ traced decisions (35)

### CORPUS-INC-CUBAN-MISSILE-CRISIS (9 scenarios, 9 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NS-29adcc55-E1@v1` | extract | 2 | Estimating the Soviet Build-Up in Cuba | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NS-29adcc55-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NS-7da388f0-E1@v1` | extract | 2 | Interpreting Cuba’s New Air-Defense Installations | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NS-7da388f0-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-338578c6-E2@v1` | extract | 2 | Assessing Possible Warhead Presence | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-338578c6-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-3779bf8d-E8@v1` | extract | 3 | Choosing a Response to the Cuban Missile Crisis | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-3779bf8d-E8@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-3779bf8d-E9@v1` | extract | 3 | Response Authority in a U-2 Contingency | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-3779bf8d-E9@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-5f794ec0-E25@v1` | extract | 2 | Diplomatic Language for Cuba Policy | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-5f794ec0-E25@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-7561f57e-E1@v1` | extract | 2 | Estimating the Soviet Military Build-up in Cuba | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-7561f57e-E1@v1.yaml` |
| B1 | gold | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-a3a879f6-E23@v1` | extract | 2 | Control of the Cuba Overflights | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-a3a879f6-E23@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-e24a01fb-E16@v1` | extract | 2 | Boarding the Intercepted Tanker | `data/store/scenarios/CORPUS-INC-CUBAN-MISSILE-CRISIS/DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-e24a01fb-E16@v1.yaml` |

### CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I (5 scenarios, 5 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NS-4ec53ab6-E1@v1` | extract | 2 | Organizing Defense Intelligence | `data/store/scenarios/CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I/DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NS-4ec53ab6-E1@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NS-4ec53ab6-E2@v1` | extract | 3 | DIA Publication and Resource Decision | `data/store/scenarios/CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I/DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NS-4ec53ab6-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-0cb5fe5a-E3@v1` | extract | 2 | Choosing DIA’s Organizational Structure | `data/store/scenarios/CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I/DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-0cb5fe5a-E3@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-5d3d2e44-E2@v1` | extract | 3 | Centralizing Defense Intelligence Management | `data/store/scenarios/CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I/DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-5d3d2e44-E2@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-6a1539ab-E1@v1` | extract | 2 | Where to Place the Defense Intelligence Agency | `data/store/scenarios/CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I/DR-CORPUS-INC-CREATION-AND-ACTIVATION-OF-THE-DEFENSE-I-NX-6a1539ab-E1@v1.yaml` |

### CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING (5 scenarios, 5 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-0077b9de-E11@v1` | extract | 3 | Review of a Pacific Warning Draft | `data/store/scenarios/CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING/DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-0077b9de-E11@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-0077b9de-E15@v1` | extract | 2 | Translation Priority on 6 December | `data/store/scenarios/CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING/DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-0077b9de-E15@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-2fc939b7-E1@v1` | extract | 2 | Estimative Judgment on a Possible Approach to Hawaii | `data/store/scenarios/CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING/DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-2fc939b7-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-dd571671-E5@v1` | extract | 2 | Warning Pearl Harbor | `data/store/scenarios/CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING/DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-dd571671-E5@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-e6eabab0-E3@v1` | extract | 2 | Dividing Responsibility for Diplomatic Messages | `data/store/scenarios/CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING/DR-CORPUS-INC-PEARL-HARBOR-ATTACK-AND-WARNING-NX-e6eabab0-E3@v1.yaml` |

### CORPUS-CHILCOT (4 scenarios, 4 distinct decisions) — gov-ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-CHILCOT-NX-249d4566-E44@v1` | extract | 3 | Civilian Repatriation and Arrival Arrangements | `data/store/scenarios/CORPUS-CHILCOT/DR-CORPUS-CHILCOT-NX-249d4566-E44@v1.yaml` |
| B1 |  | `DR-CORPUS-CHILCOT-NX-249d4566-E59@v1` | extract | 3 | Fitness Assessment for Iraq Postings | `data/store/scenarios/CORPUS-CHILCOT/DR-CORPUS-CHILCOT-NX-249d4566-E59@v1.yaml` |
| B1 |  | `DR-CORPUS-CHILCOT-NX-b15898a1-E34@v1` | extract | 2 | UK Participation in a Proposed Allied Action | `data/store/scenarios/CORPUS-CHILCOT/DR-CORPUS-CHILCOT-NX-b15898a1-E34@v1.yaml` |
| B1 | other | `DR-CORPUS-CHILCOT-NX-fe3dbf91-E46@v1` | extract | 4 | Immediate Action or a Phased Security Plan | `data/store/scenarios/CORPUS-CHILCOT/DR-CORPUS-CHILCOT-NX-fe3dbf91-E46@v1.yaml` |

### CORPUS-INC-BATTLE-OF-SAVO-ISLAND (4 scenarios, 4 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | other | `DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-1d4cbeb1-E10@v1` | extract | 3 | Revising the Carrier-Group Employment Schedule | `data/store/scenarios/CORPUS-INC-BATTLE-OF-SAVO-ISLAND/DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-1d4cbeb1-E10@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-1d4cbeb1-E29@v1` | extract | 2 | Force Assignments for the Decisive Battle | `data/store/scenarios/CORPUS-INC-BATTLE-OF-SAVO-ISLAND/DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-1d4cbeb1-E29@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-7dd6b155-E33@v1` | extract | 3 | Changing an Assigned Patrol During an Emerging Battle | `data/store/scenarios/CORPUS-INC-BATTLE-OF-SAVO-ISLAND/DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-7dd6b155-E33@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-ef488ef8-E14@v1` | extract | 3 | The Night Attack Decision | `data/store/scenarios/CORPUS-INC-BATTLE-OF-SAVO-ISLAND/DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-ef488ef8-E14@v1.yaml` |

### CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1 (4 scenarios, 4 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-751847be-E2@v1` | extract | 2 | Assessing the Warning of PRC Intervention | `data/store/scenarios/CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1/DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-751847be-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-ed69d2d6-E2@v1` | extract | 3 | CIA Leadership After the Korean Invasion | `data/store/scenarios/CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1/DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-ed69d2d6-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-ed69d2d6-E3@v1` | extract | 2 | Estimating Chinese Intervention in Korea | `data/store/scenarios/CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1/DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-ed69d2d6-E3@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-f0333cf6-E4@v1` | extract | 2 | Assessing Chinese Intervention in Korea | `data/store/scenarios/CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1/DR-CORPUS-INC-CHINESE-INTERVENTION-WARNINGS-IN-KOREA-1-NX-f0333cf6-E4@v1.yaml` |

### CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE- (4 scenarios, 4 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-95035954-E25@v1` | extract | 2 | Elevating Source-Reliability Concerns Before a Speech | `data/store/scenarios/CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE-/DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-95035954-E25@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-b4eef3c7-E8@v1` | extract | 2 | Escalating Doubts Before the United Nations Address | `data/store/scenarios/CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE-/DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-b4eef3c7-E8@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-b4eef3c7-E9@v1` | extract | 3 | When to Correct the Mobile BW Assessment | `data/store/scenarios/CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE-/DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NS-b4eef3c7-E9@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NX-fa69577e-E1@v1` | extract | 2 | Reassessing a Source’s Credibility | `data/store/scenarios/CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE-/DR-CORPUS-INC-CURVEBALL-AND-THE-IRAQ-WMD-INTELLIGENCE--NX-fa69577e-E1@v1.yaml` |

### CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH (4 scenarios, 4 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-e065dfb0-E1@v1` | extract | 2 | The Inchon Approval Decision | `data/store/scenarios/CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH/DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-e065dfb0-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-f11520ad-E1@v1` | extract | 2 | Choosing the Inchon Course of Action | `data/store/scenarios/CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH/DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-f11520ad-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-fc6abcb5-E2@v1` | extract | 2 | Estimating Soviet Choices in Korea | `data/store/scenarios/CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH/DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-fc6abcb5-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-fc6abcb5-E5@v1` | extract | 4 | Soviet Response to the Changed Korean Situation | `data/store/scenarios/CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH/DR-CORPUS-INC-INCHON-LANDING-AND-ITS-AFTERMATH-NX-fc6abcb5-E5@v1.yaml` |

### CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE (4 scenarios, 4 distinct decisions) — operational-command

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | other | `DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NS-be8010b5-E17@v1` | extract | 2 | Countryside Operations or Capital Defense | `data/store/scenarios/CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE/DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NS-be8010b5-E17@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-4c6f4cdb-E1@v1` | extract | 2 | Force Restrictions in Old Hue | `data/store/scenarios/CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE/DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-4c6f4cdb-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-4c6f4cdb-E2@v1` | extract | 2 | Reinforcing the Effort Northwest of Hue | `data/store/scenarios/CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE/DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-4c6f4cdb-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-c4d37023-E2@v1` | extract | 2 | Resist or Surrender Under Attack | `data/store/scenarios/CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE/DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NX-c4d37023-E2@v1.yaml` |

### CORPUS-NX-09fb3b9c (4 scenarios, 4 distinct decisions) — cyber-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-NX-09fb3b9c-E1@v1` | extract | 3 | Binding Cybersecurity Requirements for Contractors | `data/store/scenarios/CORPUS-NX-09fb3b9c/DR-CORPUS-NX-09fb3b9c-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-09fb3b9c-E2@v1` | extract | 3 | Supermicro Supplier Relationship | `data/store/scenarios/CORPUS-NX-09fb3b9c/DR-CORPUS-NX-09fb3b9c-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-09fb3b9c-E3@v1` | extract | 2 | Cybersecurity Certification for Defense Contracts | `data/store/scenarios/CORPUS-NX-09fb3b9c/DR-CORPUS-NX-09fb3b9c-E3@v1.yaml` |
| B1 | gold | `DR-CORPUS-NX-09fb3b9c-E4@v1` | extract | 3 | Aegis Server Supply-Chain Risk Review | `data/store/scenarios/CORPUS-NX-09fb3b9c/DR-CORPUS-NX-09fb3b9c-E4@v1.yaml` |

### CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI (3 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  | other | `DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-89977472-E1@v1` | extract | 2 | Ground-Control Authority for a Patrol Engagement | `data/store/scenarios/CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI/DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-89977472-E1@v1.yaml` |
|  | gold | `DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-89977472-E2@v1` | extract | 2 | Responding to a Friendly-Forces Warning | `data/store/scenarios/CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI/DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-89977472-E2@v1.yaml` |
|  | other | `DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-f8a09055-E1@v1` | extract | 2 | Unresolved Identification Before Engagement | `data/store/scenarios/CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI/DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-f8a09055-E1@v1.yaml` |

### CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE (3 scenarios, 3 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | gold | `DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-879619ff-E1@v1` | extract | 2 | Briefing Presidential Candidates | `data/store/scenarios/CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE/DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-879619ff-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-de686566-E2@v1` | extract | 2 | Candidate Intelligence Briefing Access | `data/store/scenarios/CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE/DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-de686566-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-de686566-E5@v1` | extract | 3 | Interrogation Policy After the Inauguration | `data/store/scenarios/CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE/DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-de686566-E5@v1.yaml` |

### CORPUS-INC-BAY-OF-PIGS-OPERATION (3 scenarios, 3 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | gold | `DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NS-2159ccc1-E3@v1` | extract | 2 | Scope of the Bay of Pigs Survey | `data/store/scenarios/CORPUS-INC-BAY-OF-PIGS-OPERATION/DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NS-2159ccc1-E3@v1.yaml` |
| B1 | gold | `DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NX-50b252eb-E4@v1` | extract | 3 | Whether to Retain the D-Day Cancellation | `data/store/scenarios/CORPUS-INC-BAY-OF-PIGS-OPERATION/DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NX-50b252eb-E4@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NX-f3087007-E1@v1` | extract | 2 | Public Commitment or Limited Covert Action | `data/store/scenarios/CORPUS-INC-BAY-OF-PIGS-OPERATION/DR-CORPUS-INC-BAY-OF-PIGS-OPERATION-NX-f3087007-E1@v1.yaml` |

### CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING (3 scenarios, 3 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NS-49be4a73-E1@v1` | extract | 2 | Assessment of a Reported Civilian-Casualty Incident Near Raqqah | `data/store/scenarios/CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING/DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NS-49be4a73-E1@v1.yaml` |
|  |  | `DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NX-7cbe5573-E1@v1` | extract | 2 | Assessment of Civilian-Casualty Allegations in Yemen | `data/store/scenarios/CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING/DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NX-7cbe5573-E1@v1.yaml` |
|  |  | `DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NX-dfb91357-E1@v1` | extract | 2 | Estimating Noncombatant Casualties | `data/store/scenarios/CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING/DR-CORPUS-INC-CIVILIAN-CASUALTY-INCIDENT-REPORTING-NX-dfb91357-E1@v1.yaml` |

### CORPUS-INC-CREATION-OF-THE-CIA (3 scenarios, 3 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-52321c2e-E2@v1` | extract | 2 | Central Intelligence Authority and Oversight | `data/store/scenarios/CORPUS-INC-CREATION-OF-THE-CIA/DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-52321c2e-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-91394f44-E1@v1` | extract | 3 | Central Intelligence and Departmental Autonomy | `data/store/scenarios/CORPUS-INC-CREATION-OF-THE-CIA/DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-91394f44-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-a17c3dba-E1@v1` | extract | 2 | The 1947 Intelligence Structure | `data/store/scenarios/CORPUS-INC-CREATION-OF-THE-CIA/DR-CORPUS-INC-CREATION-OF-THE-CIA-NX-a17c3dba-E1@v1.yaml` |

### CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT (3 scenarios, 3 distinct decisions) — operational-command

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-2e126ea7-E1@v1` | extract | 2 | Choosing a Southern-Front Structure | `data/store/scenarios/CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT/DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-2e126ea7-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-5cbbcf57-E8@v1` | extract | 2 | Nicaragua Intervention Decision | `data/store/scenarios/CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT/DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-5cbbcf57-E8@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-b37dd2f6-E2@v1` | extract | 3 | Choosing a Southern Front | `data/store/scenarios/CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT/DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-b37dd2f6-E2@v1.yaml` |

### CORPUS-INC-OPERATION-DESERT-STORM (3 scenarios, 3 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-ce0aec42-E1@v1` | extract | 2 | Measuring Counter-SRBM Campaign Effectiveness | `data/store/scenarios/CORPUS-INC-OPERATION-DESERT-STORM/DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-ce0aec42-E1@v1.yaml` |
|  |  | `DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-f4d2fcaf-E1@v1` | extract | 2 | Revising the Marine Operation Plan | `data/store/scenarios/CORPUS-INC-OPERATION-DESERT-STORM/DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-f4d2fcaf-E1@v1.yaml` |
|  |  | `DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-f4d2fcaf-E2@v1` | extract | 2 | Response to the Iraqi Deployment Near Kuwait | `data/store/scenarios/CORPUS-INC-OPERATION-DESERT-STORM/DR-CORPUS-INC-OPERATION-DESERT-STORM-NX-f4d2fcaf-E2@v1.yaml` |

### CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1 (3 scenarios, 3 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-2db78145-E6@v1` | extract | 3 | Estimating the Risk of Martial Law | `data/store/scenarios/CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1/DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-2db78145-E6@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-52315bc7-E2@v1` | extract | 2 | Whether to Warn Solidarity | `data/store/scenarios/CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1/DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-52315bc7-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-8668b50f-E9@v1` | extract | 2 | Whether to Move Forces into Poland for a Planned Exercise | `data/store/scenarios/CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1/DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-8668b50f-E9@v1.yaml` |

### CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS (3 scenarios, 3 distinct decisions) — natsec-other

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NS-664e6171-E1@v1` | extract | 3 | Pre-Departure Communications-Security Inventory | `data/store/scenarios/CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS/DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NS-664e6171-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NS-664e6171-E2@v1` | extract | 2 | Response to Compromised January Keying Material | `data/store/scenarios/CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS/DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NS-664e6171-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NX-c8381898-E1@v1` | extract | 2 | Reply Content Under Time Pressure | `data/store/scenarios/CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS/DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NX-c8381898-E1@v1.yaml` |

### CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM (3 scenarios, 3 distinct decisions) — intel-oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-99356abd-E2@v1` | extract | 2 | Secret Campaign Funding in Italy | `data/store/scenarios/CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM/DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-99356abd-E2@v1.yaml` |
| B1 | other | `DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-99356abd-E3@v1` | extract | 3 | Disclosure of Past CIA Actions to Congress | `data/store/scenarios/CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM/DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-99356abd-E3@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-aacf06ad-E1@v1` | extract | 2 | Italy's 1948 Election Intervention Decision | `data/store/scenarios/CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM/DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-aacf06ad-E1@v1.yaml` |

### CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU (3 scenarios, 3 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-2660676c-E38@v1` | extract | 3 | Judging Whether Soviet Strategic Thinking Has Changed | `data/store/scenarios/CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU/DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-2660676c-E38@v1.yaml` |
| B1 | gold | `DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-2660676c-E3@v1` | extract | 2 | Force and Soviet Influence in Eastern Europe | `data/store/scenarios/CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU/DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-2660676c-E3@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-62bccee7-E4@v1` | extract | 2 | Intervention as a Last Resort in East Europe | `data/store/scenarios/CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU/DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-62bccee7-E4@v1.yaml` |

### CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS (3 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | gold | `DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NS-e5e4b57e-E10@v1` | extract | 3 | Urgent Inbound Aircraft Authorization | `data/store/scenarios/CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS/DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NS-e5e4b57e-E10@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NS-e5e4b57e-E18@v1` | extract | 3 | Response to the Embassy Bombings | `data/store/scenarios/CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS/DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NS-e5e4b57e-E18@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NX-dcf662c6-E1@v1` | extract | 2 | Immediate Retaliation Decision | `data/store/scenarios/CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS/DR-CORPUS-INC-U-S-RESPONSE-TO-THE-SEPTEMBER-11-ATTACKS-NX-dcf662c6-E1@v1.yaml` |

### CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010 (3 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NS-a5e6c4f4-E1@v1` | extract | 2 | Whether to Use Force Against a Convoy | `data/store/scenarios/CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010/DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NS-a5e6c4f4-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NX-55e3aba8-E1@v1` | extract | 3 | Imminent-Threat Engagement Decision | `data/store/scenarios/CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010/DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NX-55e3aba8-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NX-ceb711f3-E1@v1` | extract | 2 | Decision on Engagement of Armed Personnel | `data/store/scenarios/CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010/DR-CORPUS-INC-URUZGAN-CONVOY-STRIKE-21-FEBRUARY-2010-NX-ceb711f3-E1@v1.yaml` |

### CORPUS-INC-YUGOSLAV-CRISIS (3 scenarios, 3 distinct decisions) — intel-analysis

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E1@v1` | extract | 2 | Reassigning the Yugoslavia Estimate Draft | `data/store/scenarios/CORPUS-INC-YUGOSLAV-CRISIS/DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E6@v1` | extract | 3 | Whether to Support Active Steps on Yugoslavia | `data/store/scenarios/CORPUS-INC-YUGOSLAV-CRISIS/DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E6@v1.yaml` |
| B1 |  | `DR-CORPUS-INC-YUGOSLAV-CRISIS-NX-8c670201-E7@v1` | extract | 2 | Organizing Intelligence Support for Yugoslavia | `data/store/scenarios/CORPUS-INC-YUGOSLAV-CRISIS/DR-CORPUS-INC-YUGOSLAV-CRISIS-NX-8c670201-E7@v1.yaml` |

### CORPUS-NS-35d7f8e7 (3 scenarios, 3 distinct decisions) — natsec-other

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | gold | `DR-CORPUS-NS-35d7f8e7-E16@v1` | extract | 3 | Detainee Transfers and Torture Risk | `data/store/scenarios/CORPUS-NS-35d7f8e7/DR-CORPUS-NS-35d7f8e7-E16@v1.yaml` |
| B1 |  | `DR-CORPUS-NS-35d7f8e7-E5@v1` | extract | 2 | Protection Pending POW Status Determination | `data/store/scenarios/CORPUS-NS-35d7f8e7/DR-CORPUS-NS-35d7f8e7-E5@v1.yaml` |
| B1 |  | `DR-CORPUS-NS-35d7f8e7-E7@v1` | extract | 2 | Deadly Force During a POW Escape Attempt | `data/store/scenarios/CORPUS-NS-35d7f8e7/DR-CORPUS-NS-35d7f8e7-E7@v1.yaml` |

### CORPUS-NS-b39d38e4 (3 scenarios, 3 distinct decisions) — natsec-other

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | other | `DR-CORPUS-NS-b39d38e4-E23@v1` | extract | 2 | Group Detention and Individualized Evidence | `data/store/scenarios/CORPUS-NS-b39d38e4/DR-CORPUS-NS-b39d38e4-E23@v1.yaml` |
| B1 |  | `DR-CORPUS-NS-b39d38e4-E45@v1` | extract | 2 | Urgency and Earlier Acquisition Planning | `data/store/scenarios/CORPUS-NS-b39d38e4/DR-CORPUS-NS-b39d38e4-E45@v1.yaml` |
| B1 |  | `DR-CORPUS-NS-b39d38e4-E51@v1` | extract | 3 | Foreign-Government Gift and Diplomatic Relations | `data/store/scenarios/CORPUS-NS-b39d38e4/DR-CORPUS-NS-b39d38e4-E51@v1.yaml` |

### CORPUS-NS-e2d8559e (3 scenarios, 3 distinct decisions) — use-of-force-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-NS-e2d8559e-E57@v1` | extract | 2 | Custody of POWs Under Operational Pressure | `data/store/scenarios/CORPUS-NS-e2d8559e/DR-CORPUS-NS-e2d8559e-E57@v1.yaml` |
|  |  | `DR-CORPUS-NS-e2d8559e-E59@v1` | extract | 2 | Temporary POW Detention Aboard a Naval Vessel | `data/store/scenarios/CORPUS-NS-e2d8559e/DR-CORPUS-NS-e2d8559e-E59@v1.yaml` |
|  | other | `DR-CORPUS-NS-e2d8559e-E68@v1` | extract | 3 | Determining Whether Active Hostilities Have Ceased | `data/store/scenarios/CORPUS-NS-e2d8559e/DR-CORPUS-NS-e2d8559e-E68@v1.yaml` |

### CORPUS-NSARCHIVE-BOP (3 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-NSARCHIVE-BOP-NX-1c6c919b-E1@v1` | extract | 3 | Whether to Preserve Air Operations | `data/store/scenarios/CORPUS-NSARCHIVE-BOP/DR-CORPUS-NSARCHIVE-BOP-NX-1c6c919b-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-NSARCHIVE-BOP-NX-3f42bccd-E2@v1` | extract | 3 | Reimbursement Under an Oral Arrangement | `data/store/scenarios/CORPUS-NSARCHIVE-BOP/DR-CORPUS-NSARCHIVE-BOP-NX-3f42bccd-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-NSARCHIVE-BOP-NX-3f42bccd-E4@v1` | extract | 2 | Authority to Commit Volunteer Personnel | `data/store/scenarios/CORPUS-NSARCHIVE-BOP/DR-CORPUS-NSARCHIVE-BOP-NX-3f42bccd-E4@v1.yaml` |

### CORPUS-NX-25c7082f (3 scenarios, 3 distinct decisions) — natsec-other

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-NX-25c7082f-E10@v1` | extract | 3 | Minefield Disclosure and Impartiality | `data/store/scenarios/CORPUS-NX-25c7082f/DR-CORPUS-NX-25c7082f-E10@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-25c7082f-E11@v1` | extract | 2 | Emergency Civilian Medical Support | `data/store/scenarios/CORPUS-NX-25c7082f/DR-CORPUS-NX-25c7082f-E11@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-25c7082f-E4@v1` | extract | 3 | Pre-emptive Force in Peacekeeping | `data/store/scenarios/CORPUS-NX-25c7082f/DR-CORPUS-NX-25c7082f-E4@v1.yaml` |

### CORPUS-NX-7b45b55b (3 scenarios, 3 distinct decisions) — cyber-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-NX-7b45b55b-E1@v1` | extract | 2 | NSA’s Role in DoD Computer-Security Management | `data/store/scenarios/CORPUS-NX-7b45b55b/DR-CORPUS-NX-7b45b55b-E1@v1.yaml` |
|  |  | `DR-CORPUS-NX-7b45b55b-E2@v1` | extract | 2 | Where to Place the Computer Security Evaluation Center | `data/store/scenarios/CORPUS-NX-7b45b55b/DR-CORPUS-NX-7b45b55b-E2@v1.yaml` |
|  |  | `DR-CORPUS-NX-7b45b55b-E3@v1` | extract | 2 | Federal SBU Computer-Security Responsibility | `data/store/scenarios/CORPUS-NX-7b45b55b/DR-CORPUS-NX-7b45b55b-E3@v1.yaml` |

### CORPUS-NX-8588d266 (3 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-NX-8588d266-E19@v1` | extract | 2 | Reprisal After an Assassination Warning | `data/store/scenarios/CORPUS-NX-8588d266/DR-CORPUS-NX-8588d266-E19@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-8588d266-E22@v1` | extract | 3 | A Time-Sensitive Strike Recommendation | `data/store/scenarios/CORPUS-NX-8588d266/DR-CORPUS-NX-8588d266-E22@v1.yaml` |
| B1 | gold | `DR-CORPUS-NX-8588d266-E89@v1` | extract | 3 | Bond Release Pending FBI Clearance | `data/store/scenarios/CORPUS-NX-8588d266/DR-CORPUS-NX-8588d266-E89@v1.yaml` |

### CORPUS-NX-c5ef1aef (3 scenarios, 3 distinct decisions) — gov-ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-NX-c5ef1aef-E10@v1` | extract | 3 | Ethics Enforcement for Technical Errors and Innocent Contacts | `data/store/scenarios/CORPUS-NX-c5ef1aef/DR-CORPUS-NX-c5ef1aef-E10@v1.yaml` |
|  |  | `DR-CORPUS-NX-c5ef1aef-E3@v1` | extract | 2 | Unifying National-Incident Response | `data/store/scenarios/CORPUS-NX-c5ef1aef/DR-CORPUS-NX-c5ef1aef-E3@v1.yaml` |
|  | gold | `DR-CORPUS-NX-c5ef1aef-E4@v1` | extract | 2 | Readiness for Conditional Preemptive Action | `data/store/scenarios/CORPUS-NX-c5ef1aef/DR-CORPUS-NX-c5ef1aef-E4@v1.yaml` |

### CORPUS-NX-d8f57d6c (3 scenarios, 3 distinct decisions) — use-of-force-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 | gold | `DR-CORPUS-NX-d8f57d6c-E1@v1` | extract | 3 | Capture Preference in Counterterrorism Policy | `data/store/scenarios/CORPUS-NX-d8f57d6c/DR-CORPUS-NX-d8f57d6c-E1@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-d8f57d6c-E2@v1` | extract | 3 | Review of a Lethal-Action Nomination | `data/store/scenarios/CORPUS-NX-d8f57d6c/DR-CORPUS-NX-d8f57d6c-E2@v1.yaml` |
| B1 |  | `DR-CORPUS-NX-d8f57d6c-E3@v1` | extract | 2 | Long-Term Disposition of a Suspect | `data/store/scenarios/CORPUS-NX-d8f57d6c/DR-CORPUS-NX-d8f57d6c-E3@v1.yaml` |

### CORPUS-NX-e6c14241 (3 scenarios, 3 distinct decisions) — use-of-force-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-CORPUS-NX-e6c14241-E1@v1` | extract | 2 | Cyber Activity and the Article 5 Threshold | `data/store/scenarios/CORPUS-NX-e6c14241/DR-CORPUS-NX-e6c14241-E1@v1.yaml` |
|  |  | `DR-CORPUS-NX-e6c14241-E2@v1` | extract | 2 | Response After Tailored Deterrence Fails | `data/store/scenarios/CORPUS-NX-e6c14241/DR-CORPUS-NX-e6c14241-E2@v1.yaml` |
|  |  | `DR-CORPUS-NX-e6c14241-E3@v1` | extract | 2 | Command Decision Timing Under Uncertainty | `data/store/scenarios/CORPUS-NX-e6c14241/DR-CORPUS-NX-e6c14241-E3@v1.yaml` |

### CORPUS-NSARCHIVE-ABLEARCHER (2 scenarios, 2 distinct decisions) — cyber-policy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| B1 |  | `DR-CORPUS-NSARCHIVE-ABLEARCHER-NX-f56769f7-E4@v1` | extract | 3 | Choosing the Computer-Security Organization | `data/store/scenarios/CORPUS-NSARCHIVE-ABLEARCHER/DR-CORPUS-NSARCHIVE-ABLEARCHER-NX-f56769f7-E4@v1.yaml` |
| B1 |  | `DR-CORPUS-NSARCHIVE-ABLEARCHER-NX-f56769f7-E9@v1` | extract | 2 | A Policy for Relocatable Soviet Missiles | `data/store/scenarios/CORPUS-NSARCHIVE-ABLEARCHER/DR-CORPUS-NSARCHIVE-ABLEARCHER-NX-f56769f7-E9@v1.yaml` |

## Older (2f) families with 2+ traced scenarios (66)

### KUNDUZ-2009 (8 scenarios, 3 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-KUNDUZ-2009-1@v1` | extract | 4 | Declaration of Troops‑in‑Contact Based on Imminent Threat | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-1@v1.yaml` |
| A1 | other | `DR-KUNDUZ-2009-2@v1` | extract | 4 | Authorization of Air Strike on Tankers on Sandbank | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-2@v1.yaml` |
| A1 | other | `DR-KUNDUZ-2009-3@v1` | extract | 2 | Accepting or Declining a Show of Force before Airstrike on Sandbank | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-3@v1.yaml` |
| A1 | gold | `DR-KUNDUZ-2009-flip1@v1` | flip | 4 | Authorization of Air Strike on Tankers on Sandbank [flip] | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-flip1@v1.yaml` |
| A1 | gold | `DR-KUNDUZ-2009-flip2@v1` | flip | 2 | Accepting or Declining a Show of Force before Airstrike on Sandbank [flip] | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-flip2@v1.yaml` |
| A1 | gold | `DR-KUNDUZ-2009-restyle1@v1` | restyle | 4 | Declaration of Troops‑in‑Contact Based on Imminent Threat [restyle] | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle1@v1.yaml` |
| A1 | other | `DR-KUNDUZ-2009-restyle2@v1` | restyle | 2 | Accepting or Declining a Show of Force before Airstrike on Sandbank [restyle] | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle2@v1.yaml` |
| A1 |  | `DR-KUNDUZ-2009-restyle3@v1` | restyle | 4 | Authorization of Air Strike on Tankers on Sandbank [restyle] | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle3@v1.yaml` |

### OGE-2635-702 (8 scenarios, 2 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | gold | `DR-OGE-2635-702-1@v1` | extract | 4 | Commerce Employee’s Request to Expedite Friend’s Export License | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-1@v1.yaml` |
| A1 | gold | `DR-OGE-2635-702-2@v1` | extract | 4 | Assistant Attorney General Book Jacket Endorsement Decision | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-2@v1.yaml` |
| A1 | gold | `DR-OGE-2635-702-addfact1@v1` | add_fact | 4 | Commerce Employee’s Request to Expedite Friend’s Export License [addfact] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-addfact1@v1.yaml` |
| A1 |  | `DR-OGE-2635-702-addfact2@v1` | add_fact | 4 | Assistant Attorney General Book Jacket Endorsement Decision [addfact] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-addfact2@v1.yaml` |
| A1 | other | `DR-OGE-2635-702-flip1@v1` | flip | 4 | Commerce Employee’s Request to Expedite Friend’s Export License [flip] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-702-flip2@v1` | flip | 4 | Assistant Attorney General Book Jacket Endorsement Decision [flip] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-flip2@v1.yaml` |
| A1 |  | `DR-OGE-2635-702-restyle1@v1` | restyle | 4 | Commerce Employee’s Request to Expedite Friend’s Export License [restyle] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-restyle1@v1.yaml` |
| A1 |  | `DR-OGE-2635-702-restyle2@v1` | restyle | 4 | Assistant Attorney General Book Jacket Endorsement Decision [restyle] | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-restyle2@v1.yaml` |

### OGE-2635-808 (7 scenarios, 2 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OGE-2635-808-1@v1` | extract | 4 | Secretary of the Navy Participation in Charity Golf Tournament | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-1@v1.yaml` |
| A1 | gold | `DR-OGE-2635-808-2@v1` | extract | 4 | Use of Agency Photocopier for Personal Fundraising | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-2@v1.yaml` |
| A1 | other | `DR-OGE-2635-808-addfact1@v1` | add_fact | 4 | Use of Agency Photocopier for Personal Fundraising [addfact] | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-addfact1@v1.yaml` |
| A1 |  | `DR-OGE-2635-808-addfact2@v1` | add_fact | 4 | Secretary of the Navy Participation in Charity Golf Tournament [addfact] | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-addfact2@v1.yaml` |
| A1 |  | `DR-OGE-2635-808-flip1@v1` | flip | 4 | Secretary of the Navy Participation in Charity Golf Tournament [flip] | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-808-restyle1@v1` | restyle | 4 | Secretary of the Navy Participation in Charity Golf Tournament [restyle] | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-restyle1@v1.yaml` |
| A1 | gold | `DR-OGE-2635-808-restyle2@v1` | restyle | 4 | Use of Agency Photocopier for Personal Fundraising [restyle] | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-restyle2@v1.yaml` |

### WCK-CONVOY-2024 (7 scenarios, 2 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-WCK-CONVOY-2024-1@v1` | extract | 3 | Engagement of Aid Convoy Vehicles | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-1@v1.yaml` |
| A1 | other | `DR-WCK-CONVOY-2024-2@v1` | extract | 2 | Decision on Continuing Strikes After Humanitarian Convoy Directive | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-2@v1.yaml` |
| A1 |  | `DR-WCK-CONVOY-2024-addfact1@v1` | add_fact | 2 | Decision on Continuing Strikes After Humanitarian Convoy Directive [addfact] | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-addfact1@v1.yaml` |
| A1 | gold | `DR-WCK-CONVOY-2024-flip1@v1` | flip | 3 | Engagement of Aid Convoy Vehicles [flip] | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-flip1@v1.yaml` |
| A1 | gold | `DR-WCK-CONVOY-2024-flip2@v1` | flip | 2 | Decision on Continuing Strikes After Humanitarian Convoy Directive [flip] | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-flip2@v1.yaml` |
| A1 | other | `DR-WCK-CONVOY-2024-restyle1@v1` | restyle | 3 | Engagement of Aid Convoy Vehicles [restyle] | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-restyle1@v1.yaml` |
| A1 | gold | `DR-WCK-CONVOY-2024-restyle2@v1` | restyle | 2 | Decision on Continuing Strikes After Humanitarian Convoy Directive [restyle] | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-restyle2@v1.yaml` |

### ICTY-NATO-1999 (6 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | gold | `DR-ICTY-NATO-1999-1@v1` | extract | 2 | Decision on Investigating Bridge Attack Incident | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-1@v1.yaml` |
| A1 | gold | `DR-ICTY-NATO-1999-addfact1@v1` | add_fact | 2 | Decision on Investigating Bridge Attack Incident [addfact] | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-addfact1@v1.yaml` |
| A1 |  | `DR-ICTY-NATO-1999-addfact2@v1` | add_fact | 3 | Bombing of RTS Broadcasting Station [addfact] | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-addfact2@v1.yaml` |
| A1 | other | `DR-ICTY-NATO-1999-flip1@v1` | flip | 2 | Decision on Investigating Bridge Attack Incident [flip] | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-flip1@v1.yaml` |
| A1 | other | `DR-ICTY-NATO-1999-flip2@v1` | flip | 3 | Bombing of RTS Broadcasting Station [flip] | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-flip2@v1.yaml` |
| A1 | gold | `DR-ICTY-NATO-1999-restyle1@v1` | restyle | 2 | Decision on Investigating Bridge Attack Incident [restyle] | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-restyle1@v1.yaml` |

### OGE-2635-304 (6 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OGE-2635-304-1@v1` | extract | 2 | CFPB Economist Gift for Supervisor's 50th Birthday | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-1@v1.yaml` |
| A1 |  | `DR-OGE-2635-304-addfact1@v1` | add_fact | 3 | Collection for Gift on Swearing‑In or Promotion [addfact] | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-addfact1@v1.yaml` |
| A1 |  | `DR-OGE-2635-304-addfact2@v1` | add_fact | 2 | CFPB Economist Gift for Supervisor's 50th Birthday [addfact] | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-addfact2@v1.yaml` |
| A1 |  | `DR-OGE-2635-304-flip1@v1` | flip | 3 | Collection for Gift on Swearing‑In or Promotion [flip] | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-304-restyle1@v1` | restyle | 2 | CFPB Economist Gift for Supervisor's 50th Birthday [restyle] | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-restyle1@v1.yaml` |
| A1 | other | `DR-OGE-2635-304-restyle2@v1` | restyle | 3 | Collection for Gift on Swearing‑In or Promotion [restyle] | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-restyle2@v1.yaml` |

### OGE-2635-502 (6 scenarios, 2 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-OGE-2635-502-1@v1` | extract | 3 | DoD Avionics Testing Employee Child's HR Job – Recusal Decision | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-1@v1.yaml` |
| A1 | other | `DR-OGE-2635-502-2@v1` | extract | 4 | IRS Audit Participation Authorization | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-2@v1.yaml` |
| A1 | other | `DR-OGE-2635-502-addfact1@v1` | add_fact | 4 | IRS Audit Participation Authorization [addfact] | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-addfact1@v1.yaml` |
| A1 | gold | `DR-OGE-2635-502-flip1@v1` | flip | 3 | DoD Avionics Testing Employee Child's HR Job – Recusal Decision [flip] | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-502-restyle1@v1` | restyle | 3 | DoD Avionics Testing Employee Child's HR Job – Recusal Decision [restyle] | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-restyle1@v1.yaml` |
| A1 | other | `DR-OGE-2635-502-restyle2@v1` | restyle | 4 | IRS Audit Participation Authorization [restyle] | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-restyle2@v1.yaml` |

### OGE-2635-807 (6 scenarios, 2 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OGE-2635-807-1@v1` | extract | 2 | SEC Employee Compensation for Securities Regulation Book | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-1@v1.yaml` |
| A1 |  | `DR-OGE-2635-807-2@v1` | extract | 4 | EEOC Employee Teaching Compensation Decision | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-2@v1.yaml` |
| A1 |  | `DR-OGE-2635-807-addfact1@v1` | add_fact | 2 | SEC Employee Compensation for Securities Regulation Book [addfact] | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-addfact1@v1.yaml` |
| A1 |  | `DR-OGE-2635-807-flip1@v1` | flip | 2 | SEC Employee Compensation for Securities Regulation Book [flip] | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-807-restyle1@v1` | restyle | 2 | SEC Employee Compensation for Securities Regulation Book [restyle] | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-restyle1@v1.yaml` |
| A1 |  | `DR-OGE-2635-807-restyle2@v1` | restyle | 4 | EEOC Employee Teaching Compensation Decision [restyle] | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-restyle2@v1.yaml` |

### TARNAK-2002 (6 scenarios, 2 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-TARNAK-2002-1@v1` | extract | 2 | Wingman's Decision to Invoke Self‑Defence ROE | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-1@v1.yaml` |
| A1 | other | `DR-TARNAK-2002-2@v1` | extract | 3 | Airborne Controller Decision on Weapon Employment Requests | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-2@v1.yaml` |
| A1 | gold | `DR-TARNAK-2002-flip1@v1` | flip | 2 | Wingman's Decision to Invoke Self‑Defence ROE [flip] | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-flip1@v1.yaml` |
| A1 | gold | `DR-TARNAK-2002-flip2@v1` | flip | 3 | Airborne Controller Decision on Weapon Employment Requests [flip] | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-flip2@v1.yaml` |
| A1 |  | `DR-TARNAK-2002-restyle1@v1` | restyle | 2 | Wingman's Decision to Invoke Self‑Defence ROE [restyle] | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-restyle1@v1.yaml` |
| A1 | other | `DR-TARNAK-2002-restyle2@v1` | restyle | 3 | Airborne Controller Decision on Weapon Employment Requests [restyle] | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-restyle2@v1.yaml` |

### OGE-2635-302 (4 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OGE-2635-302-addfact1@v1` | add_fact | 2 | Rent‑free vacation house use by a new supervisor [addfact] | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-addfact1@v1.yaml` |
| A1 | other | `DR-OGE-2635-302-flip1@v1` | flip | 2 | Rent‑free vacation house use by a new supervisor [flip] | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-302-restyle1@v1` | restyle | 2 | Rent‑free vacation house use by a new supervisor [restyle] | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-restyle1@v1.yaml` |
| A1 |  | `DR-OGE-2635-302@v1` | extract | 2 | Rent‑free vacation house use by a new supervisor | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302@v1.yaml` |

### OGE-2635-403 (4 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OGE-2635-403-addfact1@v1` | add_fact | 2 | Agency Requirement to Divest Stock for Promotion [addfact] | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-addfact1@v1.yaml` |
| A1 |  | `DR-OGE-2635-403-flip1@v1` | flip | 2 | Agency Requirement to Divest Stock for Promotion [flip] | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-flip1@v1.yaml` |
| A1 |  | `DR-OGE-2635-403-restyle1@v1` | restyle | 2 | Agency Requirement to Divest Stock for Promotion [restyle] | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-restyle1@v1.yaml` |
| A1 |  | `DR-OGE-2635-403@v1` | extract | 2 | Agency Requirement to Divest Stock for Promotion | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403@v1.yaml` |

### OGE-2635-503 (4 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-503-addfact1@v1` | add_fact | 4 | Recusal period for architect after covered payment [addfact] | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-addfact1@v1.yaml` |
|  |  | `DR-OGE-2635-503-flip1@v1` | flip | 4 | Recusal period for architect after covered payment [flip] | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-503-restyle1@v1` | restyle | 4 | Recusal period for architect after covered payment [restyle] | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-503@v1` | extract | 4 | Recusal period for architect after covered payment | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503@v1.yaml` |

### OHA-26-0020 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OHA-26-0020-addfact1@v1` | add_fact | 4 | Guideline F Financial Considerations Clearance Decision [addfact] | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-addfact1@v1.yaml` |
| A1 | other | `DR-OHA-26-0020-flip1@v1` | flip | 4 | Guideline F Financial Considerations Clearance Decision [flip] | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-flip1@v1.yaml` |
| A1 | other | `DR-OHA-26-0020-restyle1@v1` | restyle | 4 | Guideline F Financial Considerations Clearance Decision [restyle] | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-restyle1@v1.yaml` |
| A1 | other | `DR-OHA-26-0020@v1` | extract | 4 | Guideline F Financial Considerations Clearance Decision | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020@v1.yaml` |

### OHA-26-0022 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-OHA-26-0022-addfact1@v1` | add_fact | 4 | DOE Personnel Security Clearance Eligibility Determination [addfact] | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-addfact1@v1.yaml` |
| A1 |  | `DR-OHA-26-0022-flip1@v1` | flip | 4 | DOE Personnel Security Clearance Eligibility Determination [flip] | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-flip1@v1.yaml` |
| A1 | other | `DR-OHA-26-0022-restyle1@v1` | restyle | 4 | DOE Personnel Security Clearance Eligibility Determination [restyle] | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-restyle1@v1.yaml` |
| A1 |  | `DR-OHA-26-0022@v1` | extract | 4 | DOE Personnel Security Clearance Eligibility Determination | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022@v1.yaml` |

### OHA-26-0029 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-OHA-26-0029-addfact1@v1` | add_fact | 4 | Guideline H Drug Involvement – Access Authorization Decision [addfact] | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-addfact1@v1.yaml` |
| A1 | other | `DR-OHA-26-0029-flip1@v1` | flip | 4 | Guideline H Drug Involvement – Access Authorization Decision [flip] | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-flip1@v1.yaml` |
| A1 | other | `DR-OHA-26-0029-restyle1@v1` | restyle | 4 | Guideline H Drug Involvement – Access Authorization Decision [restyle] | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-restyle1@v1.yaml` |
| A1 | other | `DR-OHA-26-0029@v1` | extract | 4 | Guideline H Drug Involvement – Access Authorization Decision | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029@v1.yaml` |

### OHA-26-0062 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-OHA-26-0062-addfact1@v1` | add_fact | 3 | Restoration of Access Authorization after Alcohol‑Related Incidents [addfact] | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-addfact1@v1.yaml` |
| A1 |  | `DR-OHA-26-0062-flip1@v1` | flip | 3 | Restoration of Access Authorization after Alcohol‑Related Incidents [flip] | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-flip1@v1.yaml` |
| A1 |  | `DR-OHA-26-0062-restyle1@v1` | restyle | 3 | Restoration of Access Authorization after Alcohol‑Related Incidents [restyle] | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-restyle1@v1.yaml` |
| A1 | gold | `DR-OHA-26-0062@v1` | extract | 3 | Restoration of Access Authorization after Alcohol‑Related Incidents | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062@v1.yaml` |

### OHA-26-0086 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0086-addfact1@v1` | add_fact | 2 | DOE Personnel Security Clearance Restoration Decision [addfact] | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0086-flip1@v1` | flip | 2 | DOE Personnel Security Clearance Restoration Decision [flip] | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0086-restyle1@v1` | restyle | 2 | DOE Personnel Security Clearance Restoration Decision [restyle] | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0086@v1` | extract | 2 | DOE Personnel Security Clearance Restoration Decision | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086@v1.yaml` |

### OHA-26-0088 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0088-addfact1@v1` | add_fact | 4 | Guideline G Alcohol Consumption Security Concern – Access Authorization Restoration [addfa | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0088-flip1@v1` | flip | 4 | Guideline G Alcohol Consumption Security Concern – Access Authorization Restoration [flip] | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0088-restyle1@v1` | restyle | 4 | Guideline G Alcohol Consumption Security Concern – Access Authorization Restoration [resty | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0088@v1` | extract | 4 | Guideline G Alcohol Consumption Security Concern – Access Authorization Restoration | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088@v1.yaml` |

### OHA-26-0090 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-OHA-26-0090-addfact1@v1` | add_fact | 4 | Guideline E Personal Conduct Security Concern Decision [addfact] | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-addfact1@v1.yaml` |
| A1 |  | `DR-OHA-26-0090-flip1@v1` | flip | 4 | Guideline E Personal Conduct Security Concern Decision [flip] | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-flip1@v1.yaml` |
| A1 | gold | `DR-OHA-26-0090-restyle1@v1` | restyle | 4 | Guideline E Personal Conduct Security Concern Decision [restyle] | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-restyle1@v1.yaml` |
| A1 |  | `DR-OHA-26-0090@v1` | extract | 4 | Guideline E Personal Conduct Security Concern Decision | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090@v1.yaml` |

### OHA-26-0100 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0100-2@v1` | extract | 3 | Resolution of Guideline J Security Concern | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-2@v1.yaml` |
|  |  | `DR-OHA-26-0100-addfact2@v1` | add_fact | 3 | Resolution of Guideline J Security Concern [addfact] | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-addfact2@v1.yaml` |
|  |  | `DR-OHA-26-0100-flip3@v1` | flip | 3 | Resolution of Guideline J Security Concern [flip] | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-flip3@v1.yaml` |
|  |  | `DR-OHA-26-0100-restyle3@v1` | restyle | 3 | Resolution of Guideline J Security Concern [restyle] | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-restyle3@v1.yaml` |

### OHA-26-0118 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0118-addfact1@v1` | add_fact | 4 | Restoration of Security Clearance for DOE Contractor [addfact] | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0118-flip1@v1` | flip | 4 | Restoration of Security Clearance for DOE Contractor [flip] | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0118-restyle1@v1` | restyle | 4 | Restoration of Security Clearance for DOE Contractor [restyle] | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0118@v1` | extract | 4 | Restoration of Security Clearance for DOE Contractor | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118@v1.yaml` |

### OHA-26-0144 (4 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 |  | `DR-OHA-26-0144-addfact1@v1` | add_fact | 3 | DOE Access Authorization Eligibility Determination [addfact] | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-addfact1@v1.yaml` |
| A1 | other | `DR-OHA-26-0144-flip1@v1` | flip | 3 | DOE Access Authorization Eligibility Determination [flip] | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-flip1@v1.yaml` |
| A1 | other | `DR-OHA-26-0144-restyle1@v1` | restyle | 3 | DOE Access Authorization Eligibility Determination [restyle] | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-restyle1@v1.yaml` |
| A1 |  | `DR-OHA-26-0144@v1` | extract | 3 | DOE Access Authorization Eligibility Determination | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144@v1.yaml` |

### STARK-1987 (4 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-STARK-1987-1@v1` | extract | 2 | Response to Approaching Potentially Hostile Aircraft | `data/store/scenarios/STARK-1987/DR-STARK-1987-1@v1.yaml` |
| A1 | gold | `DR-STARK-1987-addfact1@v1` | add_fact | 2 | Response to Approaching Potentially Hostile Aircraft [addfact] | `data/store/scenarios/STARK-1987/DR-STARK-1987-addfact1@v1.yaml` |
| A1 | other | `DR-STARK-1987-flip1@v1` | flip | 2 | Response to Approaching Potentially Hostile Aircraft [flip] | `data/store/scenarios/STARK-1987/DR-STARK-1987-flip1@v1.yaml` |
| A1 | gold | `DR-STARK-1987-restyle1@v1` | restyle | 2 | Response to Approaching Potentially Hostile Aircraft [restyle] | `data/store/scenarios/STARK-1987/DR-STARK-1987-restyle1@v1.yaml` |

### VINCENNES-1988 (4 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
| A1 | other | `DR-VINCENNES-1988-1@v1` | extract | 2 | Decision to Engage Unidentified Aircraft | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-1@v1.yaml` |
| A1 | gold | `DR-VINCENNES-1988-addfact1@v1` | add_fact | 2 | Decision to Engage Unidentified Aircraft [addfact] | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-addfact1@v1.yaml` |
| A1 |  | `DR-VINCENNES-1988-flip1@v1` | flip | 2 | Decision to Engage Unidentified Aircraft [flip] | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-flip1@v1.yaml` |
| A1 |  | `DR-VINCENNES-1988-restyle1@v1` | restyle | 2 | Decision to Engage Unidentified Aircraft [restyle] | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-restyle1@v1.yaml` |

### ANACONDA-2002 (3 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-ANACONDA-2002-1@v1` | extract | 2 | Simultaneous vs Sequential Launch of Operation Anaconda | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-1@v1.yaml` |
|  |  | `DR-ANACONDA-2002-flip1@v1` | flip | 2 | Simultaneous vs Sequential Launch of Operation Anaconda [flip] | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-flip1@v1.yaml` |
|  |  | `DR-ANACONDA-2002-restyle1@v1` | restyle | 2 | Simultaneous vs Sequential Launch of Operation Anaconda [restyle] | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-restyle1@v1.yaml` |

### BLACKHAWK-SHOOTDOWN-1994 (3 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-BLACKHAWK-1994-1@v1` | extract | 2 | Engagement Decision Over Unidentified Helicopters | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-1994-1@v1.yaml` |
|  |  | `DR-BLACKHAWK-SHOOTDOWN-1994-addfact1@v1` | add_fact | 2 | Engagement Decision Over Unidentified Helicopters [addfact] | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-SHOOTDOWN-1994-addfact1@v1.yaml` |
|  |  | `DR-BLACKHAWK-SHOOTDOWN-1994-flip1@v1` | flip | 2 | Engagement Decision Over Unidentified Helicopters [flip] | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-SHOOTDOWN-1994-flip1@v1.yaml` |

### FARAH-2009 (3 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-FARAH-2009-1@v1` | extract | 4 | Strike Decision on Unverified Target | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-1@v1.yaml` |
|  |  | `DR-FARAH-2009-addfact1@v1` | add_fact | 4 | Strike Decision on Unverified Target [addfact] | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-addfact1@v1.yaml` |
|  |  | `DR-FARAH-2009-flip1@v1` | flip | 4 | Strike Decision on Unverified Target [flip] | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-flip1@v1.yaml` |

### HARIM-2014 (3 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-HARIM-2014-1@v1` | extract | 3 | Lift No‑Strike Restriction on Compounds 001 and 002 | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-1@v1.yaml` |
|  |  | `DR-HARIM-2014-flip1@v1` | flip | 3 | Lift No‑Strike Restriction on Compounds 001 and 002 [flip] | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-flip1@v1.yaml` |
|  |  | `DR-HARIM-2014-restyle1@v1` | restyle | 3 | Lift No‑Strike Restriction on Compounds 001 and 002 [restyle] | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-restyle1@v1.yaml` |

### MOSUL-ALJADIDA-2017 (3 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-MOSUL-ALJADIDA-2017-1@v1` | extract | 2 | Approval of strike on building housing ISIS snipers | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-1@v1.yaml` |
|  |  | `DR-MOSUL-ALJADIDA-2017-flip1@v1` | flip | 2 | Approval of strike on building housing ISIS snipers [flip] | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-flip1@v1.yaml` |
|  |  | `DR-MOSUL-ALJADIDA-2017-restyle1@v1` | restyle | 2 | Approval of strike on building housing ISIS snipers [restyle] | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-restyle1@v1.yaml` |

### OGE-2635-206 (3 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-206-flip1@v1` | flip | 4 | Disposition of $200 Barometer Gift [flip] | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-206-restyle1@v1` | restyle | 4 | Disposition of $200 Barometer Gift [restyle] | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-206@v1` | extract | 4 | Disposition of $200 Barometer Gift | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206@v1.yaml` |

### OGE-2635-402 (3 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-402-flip1@v1` | flip | 4 | FDA Employee Spouse Employment and Artificial Limb Approval [flip] | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-402-restyle1@v1` | restyle | 4 | FDA Employee Spouse Employment and Artificial Limb Approval [restyle] | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-402@v1` | extract | 4 | FDA Employee Spouse Employment and Artificial Limb Approval | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402@v1.yaml` |

### OGE-2635-603 (3 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-603-flip1@v1` | flip | 2 | Determination of Seeking Employment for DCAA Auditor [flip] | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-603-restyle1@v1` | restyle | 2 | Determination of Seeking Employment for DCAA Auditor [restyle] | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-603@v1` | extract | 2 | Determination of Seeking Employment for DCAA Auditor | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603@v1.yaml` |

### OGE-2635-606 (3 scenarios, 0 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-606-addfact1@v1` | add_fact | 3 | Recusal Decision for Military Officer with Prospective Defense Contractor Employment [addf | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-addfact1@v1.yaml` |
|  |  | `DR-OGE-2635-606-flip1@v1` | flip | 3 | Recusal Decision for Military Officer with Prospective Defense Contractor Employment [flip | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-606-restyle1@v1` | restyle | 3 | Recusal Decision for Military Officer with Prospective Defense Contractor Employment [rest | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-restyle1@v1.yaml` |

### OGE-2635-704 (3 scenarios, 0 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-704-addfact1@v1` | add_fact | 4 | CFTC Employee Use of Commercial Investor Service [addfact] | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-addfact1@v1.yaml` |
|  |  | `DR-OGE-2635-704-flip1@v1` | flip | 4 | CFTC Employee Use of Commercial Investor Service [flip] | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-704-restyle1@v1` | restyle | 4 | CFTC Employee Use of Commercial Investor Service [restyle] | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-restyle1@v1.yaml` |

### OGE-2635-705 (3 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-705-addfact1@v1` | add_fact | 3 | HUD Supervisory Employee Requesting Subordinate's Personal Services [addfact] | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705-addfact1@v1.yaml` |
|  |  | `DR-OGE-2635-705-restyle1@v1` | restyle | 3 | HUD Supervisory Employee Requesting Subordinate's Personal Services [restyle] | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-705@v1` | extract | 3 | HUD Supervisory Employee Requesting Subordinate's Personal Services | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705@v1.yaml` |

### OGE-2635-802 (3 scenarios, 1 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-802-flip1@v1` | flip | 2 | IRS Employee Participation in Tax-Exempt Status Determination [flip] | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-802-restyle1@v1` | restyle | 2 | IRS Employee Participation in Tax-Exempt Status Determination [restyle] | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802-restyle1@v1.yaml` |
|  |  | `DR-OGE-2635-802@v1` | extract | 2 | IRS Employee Participation in Tax-Exempt Status Determination | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802@v1.yaml` |

### OHA-25-0123 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-25-0123-addfact1@v1` | add_fact | 3 | Restoration of DOE Security Clearance after Alcohol-Related Conduct [addfact] | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123-addfact1@v1.yaml` |
|  |  | `DR-OHA-25-0123-restyle1@v1` | restyle | 3 | Restoration of DOE Security Clearance after Alcohol-Related Conduct [restyle] | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123-restyle1@v1.yaml` |
|  |  | `DR-OHA-25-0123@v1` | extract | 3 | Restoration of DOE Security Clearance after Alcohol-Related Conduct | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123@v1.yaml` |

### OHA-26-0011 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0011-addfact1@v1` | add_fact | 4 | DOE Security Clearance Restoration Decision [addfact] | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0011-restyle1@v1` | restyle | 4 | DOE Security Clearance Restoration Decision [restyle] | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0011@v1` | extract | 4 | DOE Security Clearance Restoration Decision | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011@v1.yaml` |

### OHA-26-0016 (3 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0016-addfact1@v1` | add_fact | 4 | Decision on Restoring Access Authorization under Guideline J [addfact] | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0016-flip1@v1` | flip | 4 | Decision on Restoring Access Authorization under Guideline J [flip] | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0016-restyle1@v1` | restyle | 4 | Decision on Restoring Access Authorization under Guideline J [restyle] | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-restyle1@v1.yaml` |

### OHA-26-0017 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0017-flip1@v1` | flip | 3 | Guideline I Psychological Condition Security Clearance Decision [flip] | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0017-restyle1@v1` | restyle | 3 | Guideline I Psychological Condition Security Clearance Decision [restyle] | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0017@v1` | extract | 3 | Guideline I Psychological Condition Security Clearance Decision | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017@v1.yaml` |

### OHA-26-0035 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0035-flip1@v1` | flip | 3 | Access Authorization Decision for Individual with Alcohol and PTSD Concerns [flip] | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0035-restyle1@v1` | restyle | 3 | Access Authorization Decision for Individual with Alcohol and PTSD Concerns [restyle] | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0035@v1` | extract | 3 | Access Authorization Decision for Individual with Alcohol and PTSD Concerns | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035@v1.yaml` |

### OHA-26-0051 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0051-addfact1@v1` | add_fact | 4 | Restoration of Access Authorization after DUI and Psychological Evaluation [addfact] | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0051-restyle1@v1` | restyle | 4 | Restoration of Access Authorization after DUI and Psychological Evaluation [restyle] | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0051@v1` | extract | 4 | Restoration of Access Authorization after DUI and Psychological Evaluation | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051@v1.yaml` |

### OHA-26-0069 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0069-addfact1@v1` | add_fact | 4 | Guideline J Criminal Conduct Security Concern Decision [addfact] | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0069-restyle1@v1` | restyle | 4 | Guideline J Criminal Conduct Security Concern Decision [restyle] | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0069@v1` | extract | 4 | Guideline J Criminal Conduct Security Concern Decision | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069@v1.yaml` |

### OHA-26-0085 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0085-addfact1@v1` | add_fact | 3 | DOE Personnel Security Clearance Restoration Decision [addfact] | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0085-restyle1@v1` | restyle | 3 | DOE Personnel Security Clearance Restoration Decision [restyle] | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0085@v1` | extract | 3 | DOE Personnel Security Clearance Restoration Decision | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085@v1.yaml` |

### OHA-26-0089 (3 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0089-addfact1@v1` | add_fact | 4 | DOE Security Clearance Restoration Decision [addfact] | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0089-flip1@v1` | flip | 4 | DOE Security Clearance Restoration Decision [flip] | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0089-restyle1@v1` | restyle | 4 | DOE Security Clearance Restoration Decision [restyle] | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-restyle1@v1.yaml` |

### OHA-26-0101 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0101-flip1@v1` | flip | 4 | Restoration of Access Authorization under Guideline F [flip] | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0101-restyle1@v1` | restyle | 4 | Restoration of Access Authorization under Guideline F [restyle] | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0101@v1` | extract | 4 | Restoration of Access Authorization under Guideline F | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101@v1.yaml` |

### OHA-26-0110 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0110-flip1@v1` | flip | 4 | Guideline G Alcohol Consumption Security Concern [flip] | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0110-restyle1@v1` | restyle | 4 | Guideline G Alcohol Consumption Security Concern [restyle] | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0110@v1` | extract | 4 | Guideline G Alcohol Consumption Security Concern | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110@v1.yaml` |

### OHA-26-0122 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0122-addfact2@v1` | add_fact | 4 | Guideline H Mitigation Determination [addfact] | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122-addfact2@v1.yaml` |
|  |  | `DR-OHA-26-0122-restyle2@v1` | restyle | 4 | Guideline H Mitigation Determination [restyle] | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122-restyle2@v1.yaml` |
|  |  | `DR-OHA-26-0122@v1` | extract | 4 | Guideline H Mitigation Determination | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122@v1.yaml` |

### OHA-26-0145 (3 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0145-flip1@v1` | flip | 4 | Restoration of DOE Security Clearance [flip] | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0145-restyle1@v1` | restyle | 4 | Restoration of DOE Security Clearance [restyle] | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0145@v1` | extract | 4 | Restoration of DOE Security Clearance | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145@v1.yaml` |

### ALJINAH-2017 (2 scenarios, 1 distinct decisions) — military-operational

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-ALJINAH-2017-1@v1` | extract | 3 | Approval of Dynamic Strike Without Religious Site Knowledge | `data/store/scenarios/ALJINAH-2017/DR-ALJINAH-2017-1@v1.yaml` |
|  |  | `DR-ALJINAH-2017-restyle1@v1` | restyle | 3 | Approval of Dynamic Strike Without Religious Site Knowledge [restyle] | `data/store/scenarios/ALJINAH-2017/DR-ALJINAH-2017-restyle1@v1.yaml` |

### AUT-001 (2 scenarios, 0 distinct decisions) — maritime autonomy

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-AUT-001-r1@v1` | import | 2 | Last Crew Member Ashore (revised) | `data/store/scenarios/AUT-001/DR-AUT-001-r1@v1.yaml` |
|  |  | `DR-AUT-001@v1` | import | 2 | Last Crew Member Ashore | `data/store/scenarios/AUT-001/DR-AUT-001@v1.yaml` |

### INT-301 (2 scenarios, 0 distinct decisions) — military intelligence oversight

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-INT-301-r1@v1` | import | 3 | Militia on the Open Web (revised) | `data/store/scenarios/INT-301/DR-INT-301-r1@v1.yaml` |
|  |  | `DR-INT-301@v1` | import | 3 | Militia on the Open Web | `data/store/scenarios/INT-301/DR-INT-301@v1.yaml` |

### OGE-2635-303 (2 scenarios, 0 distinct decisions) — federal employee gifts and ethics

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OGE-2635-303-flip1@v1` | flip | 4 | Farewell Lunch Acceptance Decision [flip] | `data/store/scenarios/OGE-2635-303/DR-OGE-2635-303-flip1@v1.yaml` |
|  |  | `DR-OGE-2635-303-restyle1@v1` | restyle | 4 | Farewell Lunch Acceptance Decision [restyle] | `data/store/scenarios/OGE-2635-303/DR-OGE-2635-303-restyle1@v1.yaml` |

### OHA-26-0005 (2 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0005-flip1@v1` | flip | 4 | Restoration of Security Clearance under Guideline G [flip] | `data/store/scenarios/OHA-26-0005/DR-OHA-26-0005-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0005-restyle1@v1` | restyle | 4 | Restoration of Security Clearance under Guideline G [restyle] | `data/store/scenarios/OHA-26-0005/DR-OHA-26-0005-restyle1@v1.yaml` |

### OHA-26-0008 (2 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0008-flip1@v1` | flip | 3 | Access Authorization Restoration Decision under Guideline I [flip] | `data/store/scenarios/OHA-26-0008/DR-OHA-26-0008-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0008-restyle1@v1` | restyle | 3 | Access Authorization Restoration Decision under Guideline I [restyle] | `data/store/scenarios/OHA-26-0008/DR-OHA-26-0008-restyle1@v1.yaml` |

### OHA-26-0012 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0012-restyle1@v1` | restyle | 4 | Restoration of Access Authorization after Alcohol-Related Incident [restyle] | `data/store/scenarios/OHA-26-0012/DR-OHA-26-0012-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0012@v1` | extract | 4 | Restoration of Access Authorization after Alcohol-Related Incident | `data/store/scenarios/OHA-26-0012/DR-OHA-26-0012@v1.yaml` |

### OHA-26-0038 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0038-flip1@v1` | flip | 4 | Guideline G Alcohol-Related Security Concern – Access Authorization Restoration [flip] | `data/store/scenarios/OHA-26-0038/DR-OHA-26-0038-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0038@v1` | extract | 4 | Guideline G Alcohol-Related Security Concern – Access Authorization Restoration | `data/store/scenarios/OHA-26-0038/DR-OHA-26-0038@v1.yaml` |

### OHA-26-0047 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0047-restyle1@v1` | restyle | 3 | Restoration of Access Authorization under Guideline F [restyle] | `data/store/scenarios/OHA-26-0047/DR-OHA-26-0047-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0047@v1` | extract | 3 | Restoration of Access Authorization under Guideline F | `data/store/scenarios/OHA-26-0047/DR-OHA-26-0047@v1.yaml` |

### OHA-26-0052 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0052-restyle1@v1` | restyle | 3 | Restoration of Access Authorization under Guideline G [restyle] | `data/store/scenarios/OHA-26-0052/DR-OHA-26-0052-restyle1@v1.yaml` |
|  |  | `DR-OHA-26-0052@v1` | extract | 3 | Restoration of Access Authorization under Guideline G | `data/store/scenarios/OHA-26-0052/DR-OHA-26-0052@v1.yaml` |

### OHA-26-0055 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0055-flip1@v1` | flip | 4 | Restoration of Access Authorization under Guideline G [flip] | `data/store/scenarios/OHA-26-0055/DR-OHA-26-0055-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0055@v1` | extract | 4 | Restoration of Access Authorization under Guideline G | `data/store/scenarios/OHA-26-0055/DR-OHA-26-0055@v1.yaml` |

### OHA-26-0074 (2 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0074-addfact1@v1` | add_fact | 4 | Denial of Access Authorization under Guideline F [addfact] | `data/store/scenarios/OHA-26-0074/DR-OHA-26-0074-addfact1@v1.yaml` |
|  |  | `DR-OHA-26-0074-restyle1@v1` | restyle | 4 | Denial of Access Authorization under Guideline F [restyle] | `data/store/scenarios/OHA-26-0074/DR-OHA-26-0074-restyle1@v1.yaml` |

### OHA-26-0106 (2 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0106-flip1@v1` | flip | 4 | Guideline G Alcohol Consumption Clearance Restoration [flip] | `data/store/scenarios/OHA-26-0106/DR-OHA-26-0106-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0106-restyle1@v1` | restyle | 4 | Guideline G Alcohol Consumption Clearance Restoration [restyle] | `data/store/scenarios/OHA-26-0106/DR-OHA-26-0106-restyle1@v1.yaml` |

### OHA-26-0108 (2 scenarios, 0 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0108-flip1@v1` | flip | 3 | DOE Personnel Security Clearance – LSD Use [flip] | `data/store/scenarios/OHA-26-0108/DR-OHA-26-0108-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0108-restyle1@v1` | restyle | 3 | DOE Personnel Security Clearance – LSD Use [restyle] | `data/store/scenarios/OHA-26-0108/DR-OHA-26-0108-restyle1@v1.yaml` |

### OHA-26-0123 (2 scenarios, 1 distinct decisions) — personnel security adjudication

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OHA-26-0123-flip1@v1` | flip | 3 | Restoration of Security Clearance after Drug Involvement [flip] | `data/store/scenarios/OHA-26-0123/DR-OHA-26-0123-flip1@v1.yaml` |
|  |  | `DR-OHA-26-0123@v1` | extract | 3 | Restoration of Security Clearance after Drug Involvement | `data/store/scenarios/OHA-26-0123/DR-OHA-26-0123@v1.yaml` |

### OVS-301 (2 scenarios, 0 distinct decisions) — oversight and records

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-OVS-301-r1@v1` | import | 4 | Records for a Laugh (revised) | `data/store/scenarios/OVS-301/DR-OVS-301-r1@v1.yaml` |
|  |  | `DR-OVS-301@v1` | import | 4 | Records for a Laugh | `data/store/scenarios/OVS-301/DR-OVS-301@v1.yaml` |

### REL-301 (2 scenarios, 0 distinct decisions) — foreign disclosure to partners

| grid | leak | scenario | kind | opts | title | scenario file |
|---|---|---|---|---|---|---|
|  |  | `DR-REL-301-r1@v1` | import | 3 | Briefing for an Ally (revised) | `data/store/scenarios/REL-301/DR-REL-301-r1@v1.yaml` |
|  |  | `DR-REL-301@v1` | import | 3 | Briefing for an Ally | `data/store/scenarios/REL-301/DR-REL-301@v1.yaml` |

## Families with one traced scenario (7)

- `DR-CORPUS-NX-98d29340-E5@v1` — `data/store/scenarios/CORPUS-NX-98d29340/DR-CORPUS-NX-98d29340-E5@v1.yaml`
- `DR-INT-103@v1` — `data/store/scenarios/INT-103/DR-INT-103@v1.yaml`
- `DR-OGE-2635-204-2@v1` — `data/store/scenarios/OGE-2635-204/DR-OGE-2635-204-2@v1.yaml`
- `DR-OHA-26-0024-flip1@v1` — `data/store/scenarios/OHA-26-0024/DR-OHA-26-0024-flip1@v1.yaml`
- `DR-OHA-26-0044@v1` — `data/store/scenarios/OHA-26-0044/DR-OHA-26-0044@v1.yaml`
- `DR-OHA-26-0087-2@v1` — `data/store/scenarios/OHA-26-0087/DR-OHA-26-0087-2@v1.yaml`
- `DR-OHA-26-0163@v1` — `data/store/scenarios/OHA-26-0163/DR-OHA-26-0163@v1.yaml`

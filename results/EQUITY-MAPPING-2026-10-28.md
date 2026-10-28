# Off-registry equity ids: proposed mapping (2026-10-28)

R81. Perturbation (revise_card, add_fact) wrote equity ids outside `data/registry/equities/pilot.yaml`. The code now
rejects them (commit 297c0daf); this table is for the scenarios that already have them. Proposals by GPT-6-Luna
(extractor role) from up to 3 uses of each id; **nothing has been changed**. Mark each row OK / other id / add.

44 ids, 54 uses in 48 scenarios.

## Map to an existing equity

| id | uses | proposed | conf. | why |
|---|---|---|---|---|
| `civilian_protection` | 1 | `civilian_life` | high | The use weighs the safety of a potentially civilian aircraft, which is covered by protecting the lives and safety of noncombatants. |
| `crew_readiness` | 1 | `mission_effect` | medium | The use weighs whether the crew is capable of carrying out the assigned weapons-engagement task, which bears on mission effectiveness. |
| `employee_fairness` | 1 | `duty_to_individual` | high | The use weighs the hardship and welfare of a specific employee when deciding whether to allow limited restoration. |
| `employee_protection` | 1 | `duty_to_individual` | high | The use weighs the rights and welfare of a specific employee, including protection from retaliation. |
| `ethical_compliance` | 1 | `complicity_risk` | high | The use weighs avoiding participation in potentially unethical work, which is covered by complicity_risk. |
| `evidence_insufficiency` | 1 | `due_process` | medium | The use weighs whether it is fair to proceed with a decision before obtaining corroborating evidence. |
| `evidence_reliability` | 1 | `analytic_integrity` | high | The use weighs the reliability of derogatory information and the need to verify it, which is covered by noting source reliability in analysis. |
| `fairness_to_individual` | 1 | `duty_to_individual` | medium | The use weighs rehabilitation and misconduct as factors affecting the rights and welfare of a specific individual. |
| `fairness_to_respondent` | 1 | `duty_to_individual` | medium | The use weighs the respondent’s individual contributions while assessing unresolved concerns, which is covered by respecting the rights and welfare of each specific person involved. |
| `friendly_force_protection` | 1 | `own_force_life` | high | The use weighs protecting friendly personnel from being mistakenly attacked, which is covered by the safety and survival of one's own personnel. |
| `mission_continuity` | 1 | `mission_effect` | medium | The use weighs whether the agency can continue administering the contract effectively, which bears on achieving the assigned mission's purpose. |
| `mission_effectiveness` | 1 | `mission_effect` | high | The use weighs whether denying the Individual’s services would impair the assigned mission’s performance, which is covered by whether the mission achieves its purpose. |
| `mission_necessity` | 1 | `own_force_life` | medium | The use justifies action by citing an imminent threat to friendly forces, which directly concerns their safety and survival. |
| `mission_success` | 1 | `mission_effect` | high | The use weighs whether approving the strike best achieves the assigned mission's purpose. |
| `mission_value` | 1 | `mission_effect` | high | The use weighs whether the barometer supports the agency’s mission, which is covered by mission_effect. |
| `mitigation_evidence` | 1 | `analytic_integrity` | medium | The use weighs whether the evidence supports its conclusion about abstinence and mitigation. |
| `mitigation_success` | 1 | `duty_to_individual` | medium | The commitment, therapy, and endorsements are weighed as evidence bearing on the Individual’s welfare and eligibility for conditional restoration. |
| `operational_continuity` | 1 | `mission_effect` | medium | The concern is maintaining the program’s ability to carry out its assigned purpose despite having no qualified replacement. |
| `partial_restoration` | 1 | `duty_to_individual` | medium | The use weighs the specific individual's welfare and demonstrated rehabilitation against security risk when deciding how much restoration to allow. |
| `procedural_fairness` | 1 | `due_process` | medium | The use weighs whether a fair process gathers relevant information before making a participation decision, which is covered by due process. |
| `prudential_caution` | 1 | `lawful_authority` | high | The uses weigh caution about whether the proposed venue is permitted under the governing regulation, which falls under acting within law. |
| `rehabilitation_potential` | 1 | `duty_to_individual` | medium | The use weighs evidence of a specific person’s recovery and welfare in assessing mitigation. |
| `rehabilitative_counseling` | 1 | `due_process` | medium | The counseling request allows financial responsibility to be assessed before the final clearance decision, supporting a fair procedure before a consequential decision. |
| `risk_mitigation` | 2 | `mission_effect` | medium | Both uses weigh whether provisional access with monitoring or verification can safeguard the mission while addressing the identified risk. |
| `security_clearance` | 1 | `due_process` | medium | The use weighs evidence in an individualized decision that may affect the person’s clearance, which is covered by fair procedures before depriving someone of rights or assets. |
| `statutory_authority` | 1 | `lawful_authority` | high | The use weighs compliance with a statutory requirement over an informal supervisory suggestion, which is covered by acting within the law and delegated authority. |

## Gaps: no registry equity covers these

| id | uses | proposed gloss | why |
|---|---|---|---|
| `appearance_of_bias` | 1 | Ensuring decisions are made impartially and free from actual or apparent conflicts of interest. | The use weighs impartiality and the appearance of a conflict of interest, which no registry gloss specifically covers. |
| `character` | 1 | character: Considering an individual's demonstrated integrity, responsibility, and prosocial conduct when assessing appropriate treatment. | The use weighs the individual's positive character and prosocial conduct, which none of the registry glosses specifically covers. |
| `contractual_obligation` | 1 | Honoring obligations and restrictions established by binding contracts and agreements. | These uses weigh compliance with an employment contract’s terms, an interest not covered by the registry’s glosses. |
| `family_support` | 1 | Supporting the welfare and well-being of service members’ families. | The uses weigh charitable educational support for service members’ families, which is broader than the registry’s gloss for own_force_life and is not covered by another gloss. |
| `financial_integrity` | 1 | Maintaining financial responsibility and reducing vulnerabilities that financial pressures may create. | The use weighs financial pressures as a security concern, and no registry gloss covers an individual's financial responsibility or vulnerability to financial pressure. |
| `information_gap` | 1 | Ensuring decision-makers have sufficient, relevant information to assess uncertainty before acting. | The use weighs insufficient intelligence and uncertainty that call for further collection, which none of the registry glosses directly covers. |
| `intelligence_need` | 1 | Ensuring decisions are informed by sufficient and relevant intelligence, especially when uncertainty could affect consequential action. | The use weighs the need to obtain sufficient intelligence before a lethal decision, which is distinct from faithfully analyzing available sources. |
| `mitigation` | 2 | Giving appropriate weight to favorable personal history and remedial evidence when assessing adverse conduct or risk. | These uses weigh favorable personal history and a pledge against an unresolved security concern, an interest not covered by any registry gloss. |
| `mitigation_candor` | 1 | Weighing candor and other mitigating personal conduct that reduces an individual's security risk. | The uses weigh candor and other mitigating personal conduct as factors reducing an individual’s security risk, which none of the registry glosses covers. |
| `national_security` | 3 | Protecting the nation from threats to its security and defense. | These uses weigh protecting national security through clearance decisions, an interest not covered by any registry gloss. |
| `operational_practicality` | 1 | Whether a decision or action is workable in light of operational conditions and constraints. | The use weighs the practical implications of continued workplace access for reinstatement, which none of the registry glosses specifically covers. |
| `policy_compliance` | 1 | Complying with applicable agency rules and policies, including required remedies for violations. | These uses weigh adherence to an agency’s internal policy, which no registry gloss directly covers. |
| `public_education` | 1 | Enabling the public to understand laws, institutions, and issues through accessible dissemination of information. | The interest is educating the public about securities regulation, which is distinct from making agency decisions and actions openly understandable. |
| `risk_aversion` | 1 | Managing exposure to uncertain risks by favoring cautious action when potential harms are significant. | The use weighs avoiding a possible security risk under uncertainty, which is not covered by any registry gloss. |
| `risk_management` | 3 | Identifying and reducing risks that could undermine safe and reliable performance or access. | The uses weigh and mitigate residual alcohol-related risk to justify monitoring or withholding access, an interest not covered by any registry gloss. |
| `risk_to_national_security` | 1 | Protecting the security of the nation from threats that could undermine its safety, institutions, or interests. | The use weighs a broad risk to national security, which is not covered by any registry gloss focused on a more specific interest. |
| `security_risk` | 5 | Protecting national security by ensuring access to sensitive information is granted only when security concerns are acceptably resolved. | These uses weigh the risk of granting security clearance while unresolved financial concerns remain, an interest not covered by the registry’s glosses. |
| `workplace_morale` | 1 | Supporting the morale, goodwill, and cohesion of people working together in an organization. | The use weighs employee goodwill and team cohesion, which no registry gloss directly covers. |

## Mapping onto pilot2 (after adding 5 equities)

`data/registry/equities/pilot2.mapping.yaml` holds this table; not applied yet. `by` = who proposed the row.

| id | uses | → pilot2 | by | note |
|---|---|---|---|---|
| `appearance_of_bias` | 1 | `impartiality` | claude |  |
| `character` | 1 | `mitigation` | claude |  |
| `civilian_protection` | 1 | `civilian_life` | gpt-6-luna |  |
| `contractual_obligation` | 1 | `lawful_authority` | claude | review: a contract's terms, not law |
| `crew_readiness` | 1 | `mission_effect` | gpt-6-luna |  |
| `employee_fairness` | 1 | `duty_to_individual` | gpt-6-luna |  |
| `employee_protection` | 1 | `duty_to_individual` | gpt-6-luna |  |
| `ethical_compliance` | 1 | `complicity_risk` | gpt-6-luna |  |
| `evidence_insufficiency` | 1 | `due_process` | gpt-6-luna |  |
| `evidence_reliability` | 1 | `analytic_integrity` | gpt-6-luna |  |
| `fairness_to_individual` | 1 | `duty_to_individual` | gpt-6-luna |  |
| `fairness_to_respondent` | 1 | `duty_to_individual` | gpt-6-luna |  |
| `family_support` | 1 | `duty_to_individual` | claude | review: charitable support for service families |
| `financial_integrity` | 1 | `security_risk` | claude |  |
| `friendly_force_protection` | 1 | `own_force_life` | gpt-6-luna |  |
| `information_gap` | 1 | `analytic_integrity` | claude |  |
| `intelligence_need` | 1 | `analytic_integrity` | claude |  |
| `mission_continuity` | 1 | `mission_effect` | gpt-6-luna |  |
| `mission_effectiveness` | 1 | `mission_effect` | gpt-6-luna |  |
| `mission_necessity` | 1 | `own_force_life` | gpt-6-luna |  |
| `mission_success` | 1 | `mission_effect` | gpt-6-luna |  |
| `mission_value` | 1 | `mission_effect` | gpt-6-luna |  |
| `mitigation` | 2 | `mitigation` | claude |  |
| `mitigation_candor` | 1 | `mitigation` | claude |  |
| `mitigation_evidence` | 1 | `mitigation` | claude |  |
| `mitigation_success` | 1 | `mitigation` | claude |  |
| `national_security` | 3 | `security_risk` | claude |  |
| `operational_continuity` | 1 | `mission_effect` | gpt-6-luna |  |
| `operational_practicality` | 1 | `mission_effect` | claude |  |
| `partial_restoration` | 1 | `mitigation` | claude |  |
| `policy_compliance` | 1 | `policy_compliance` | claude |  |
| `procedural_fairness` | 1 | `due_process` | gpt-6-luna |  |
| `prudential_caution` | 1 | `lawful_authority` | gpt-6-luna |  |
| `public_education` | 1 | `public_transparency` | claude | review: educating the public about a regulator's work |
| `rehabilitation_potential` | 1 | `mitigation` | claude |  |
| `rehabilitative_counseling` | 1 | `mitigation` | claude |  |
| `risk_aversion` | 1 | `security_risk` | claude |  |
| `risk_management` | 3 | `security_risk` | claude |  |
| `risk_mitigation` | 2 | `security_risk` | claude |  |
| `risk_to_national_security` | 1 | `security_risk` | claude |  |
| `security_clearance` | 1 | `security_risk` | claude |  |
| `security_risk` | 5 | `security_risk` | claude |  |
| `statutory_authority` | 1 | `lawful_authority` | gpt-6-luna |  |
| `workplace_morale` | 1 | `mission_effect` | claude | review: team cohesion |

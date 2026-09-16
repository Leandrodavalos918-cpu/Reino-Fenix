# REINO FÉNIX — MASTER WORLD DESIGN

## Vision
Persistent autonomous world simulation. The observer is external and has God Mode. The future is not scripted: rules and world state generate decisions, events, consequences and chronicles.

## World foundation
- Two sovereign kingdoms: Aurelia and Valdoria.
- Six principal cities: Puerto Alba, Río Claro, Bosque Alto, Corona, Monteluz and Bahía Gris.
- Six geographic regions linked to the cities.
- Physical roads/routes with distance, condition, security and possible blockage.
- Natural resources: grain, wood, iron, coal, stone, wool, livestock, fish, salt, wine and tools.
- Geography affects agriculture, extraction, travel, trade, prices, migration, military logistics and conflict.

## Society and population
Every person is an individual simulation entity with:
- identity, age, sex, health and mortality;
- household/family membership;
- occupation and wealth;
- personality traits, ambition and loyalty;
- relationships, trust and resentment;
- memories and individual knowledge;
- parents, spouse and descendants where applicable.

Population changes through births, deaths, aging, marriage, separation, migration and generations. No individual has privileged status merely because they are known to the observer.

## Noble structure
- 40 significant noble houses, 20 per kingdom.
- Houses have members, titles, prestige, wealth, estates, political relationships, obligations, rivals and succession order.
- Noble power changes through inheritance, marriage, debt, office, trade, war, law, reputation and economic performance.
- Succession must follow actual family relationships and world circumstances.

## Information and memory
NPCs have different knowledge. A fact may be true or false, known or unknown, recent or outdated, and held with different confidence. Information can spread socially and mutate into rumors. Secrets remain hidden unless discovered or divinely revealed. Personal memories record meaningful experiences and can affect later choices.

## Economy
The target causal loop is:
production -> employment -> wages -> consumption -> inventory -> supply/demand -> prices -> trade -> taxes -> investment/debt -> profit/loss -> business growth or bankruptcy.

Businesses have owners, workers, cash, inventory, debt, reputation and operating status. Markets vary by city. Transport capacity and route conditions affect availability and prices. Wealth must not be generated only through arbitrary random adjustments.

## Politics and government
Each kingdom has three autonomous factions and major offices. Political actors have interests, influence, alliances, obligations and rivalries. Governments can tax, spend, appoint, legislate, negotiate, respond to shortages and unrest, and change policy. Outcomes arise from actor incentives and circumstances rather than a predetermined winner.

## Crime, justice and security
Crime can produce victims, suspects, evidence, investigations, arrests, trials, judgments and consequences. Local security changes with guards, crime, unrest, infrastructure and conflict. Legal outcomes can affect wealth, reputation, relationships and politics.

## Military
Armies have soldiers, commanders, morale and supplies. Military action depends on logistics, geography, roads, food, equipment, intelligence, political authorization and morale. Conflict has causes and consequences and can alter population, infrastructure, trade and politics.

## Environment
Weather and natural conditions can influence crops, travel, health, production, prices and military logistics. Environmental effects should propagate through the economy and society rather than appear only as narrative text.

## Time and persistence
The world advances in days and can continue while the observer is absent. Long periods should be processed safely and deterministically enough to permit debugging. Years cause aging; generations reshape families and political/economic structures.

## Autonomous NPC decision model
For meaningful NPCs, decisions should consider:
1. current needs;
2. personal goals and ambitions;
3. resources and wealth;
4. relationships and obligations;
5. knowledge and uncertainty;
6. personality;
7. local conditions;
8. expected consequences;
9. recent memories;
10. available actions.

NPCs can choose not to act. They can make mistakes because their information can be incomplete or false.

## Events and causality
Important events must store cause and consequence. Narration reads from actual state/events. The narrator must not invent major facts independently of the simulation.

Example causal chain:
poor harvest -> grain scarcity -> price rise -> household consumption falls -> merchant imports grain -> transport demand rises -> debt increases -> government revenue changes -> political factions react -> public unrest may rise.

## Deep Chronicle
When the observer advances a period, the chronicle should reconstruct meaningful events from that period: demographic changes, economy, politics, travel/trade, crime/justice, military events, disasters, family events and other consequential developments. Importance determines narrative space.

## God Mode
The observer can inspect and intervene without becoming an in-world character. Supported conceptual powers include:
- create/reveal/erase information;
- modify wealth/resources/health;
- alter relationships;
- send letters;
- alter weather;
- create conflicts;
- save or kill individuals;
- schedule future interventions.

Every intervention must be logged and produce traceable consequences. NPCs never know the observer exists unless the world rules are explicitly changed.

## Long-term goals
1. Geography and territorial hierarchy.
2. Noble houses and succession.
3. Autonomous NPC decision engine.
4. Individual knowledge propagation and memory effects.
5. Causal economy and business lifecycle.
6. Autonomous government and politics.
7. Crime, justice and military logistics.
8. Robust long-period simulation and catch-up.
9. Deep Chronicle generated from real state.
10. Full God Mode with causal interventions.
11. Long-duration automated verification.

## Non-negotiable quality rule
A feature is not considered complete merely because its endpoint or UI exists. It must change and persist the intended state, interact correctly with other systems, survive multiple simulation periods, and be covered by tests where practical.

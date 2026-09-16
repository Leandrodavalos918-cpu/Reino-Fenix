# Implementation status — v2.1 package

## Verified in this package
- FastAPI application starts through `server:app`.
- SQLite persistence and locking configuration.
- Two kingdoms and six principal cities.
- Initial population/families.
- Individual people, relationships and basic knowledge records.
- Businesses and resource markets.
- Routes/shipments structures.
- Factions and offices.
- Armies/conflicts structures.
- Events and chronicles.
- Weather/projects/laws structures.
- Regions, settlements, noble houses, house members, estates and roads from the v2.1 expansion.
- Basic God Mode interventions and scheduled interventions.
- Time advancement.
- The included `test_world.py` passes locally in Python 3.13 in the build environment.

## Master-design items still requiring deeper engine work
The package intentionally documents, rather than falsely claims complete implementation of, advanced systems such as full utility-based NPC planning, realistic information propagation/rumor distortion, complete production/consumption accounting, labor markets, banking/credit, bankruptcy, autonomous government decisions, full justice investigations/trials, military logistics/combat resolution, migration dynamics, and robust multi-year catch-up.

These are the next development layers. They should be implemented incrementally and verified with long-duration tests before being called complete.

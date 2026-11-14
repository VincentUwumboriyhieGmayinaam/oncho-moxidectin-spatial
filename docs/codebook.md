# Codebook

Variables used by the analysis code. Counts refer to all 1,200 respondents (400 per round). No individual values are included.

| Variable | Description | Type | Non-missing (n) | Values / range |
|---|---|---|---|---|
| `round` | Survey round: 1 = ivermectin (Sep 2024), 2 = moxidectin 1 (Apr 2025), 3 = moxidectin 2 (Feb 2026) | numeric | 1200 | 1, 2, 3 |
| `subdistrict` | Sub-district (1-5) | numeric | 1200 | 1, 2, 3, 4, 5 |
| `community` | Community code C01-C22 (key held by study team) | numeric | 1200 | 1 to 22 |
| `interviewer` | Interviewer (1-6) | numeric | 1200 | 1, 2, 3, 4, 5, 6 |
| `age` | Age in completed years | numeric | 1199 | 14 to 100 |
| `age_grp` | Age group: 1 = 14-24, 2 = 25-34, 3 = 35-44, 4 = 45-54, 5 = 55-64, 6 = >=65 | numeric | 1199 | 1.0, 2.0, 3.0, 4.0, 5.0, 6.0 |
| `female` | Sex (1 = female) | numeric | 1200 | 0.0, 1.0 |
| `educ4` | Education: 0 = none, 1 = primary, 2 = JHS/middle, 3 = SHS or higher | numeric | 1199 | 0.0, 1.0, 2.0, 3.0 |
| `farming_hh` | Farming is main household income (1 = yes) | numeric | 1200 | 0.0, 1.0 |
| `permanent_res` | Permanent resident of the community (1 = yes) | numeric | 1199 | 0.0, 1.0 |
| `ses_index` | Household wealth index (first principal component of assets, housing, sanitation) | numeric | 1200 | -2.12036 to 6.8239 |
| `ses_q` | Wealth quintile within round (1 = poorest) | numeric | 1200 | 1.0, 2.0, 3.0, 4.0, 5.0 |
| `recall_mda` | Recalled the index MDA (1 = yes) | numeric | 1200 | 0.0, 1.0 |
| `received` | Reported receiving the medicine at the index MDA, among recallers (1 = yes; primary outcome) | numeric | 1091 | 0.0, 1.0 |
| `received_itt` | Reported receiving the medicine, non-recallers coded 0 (survey coverage) | numeric | 1200 | 0.0, 1.0 |
| `reason_not_received` | Main reason for not receiving: 1 = away, 2 = refused, 3 = not eligible, 4 = distributor did not come, 5 = other | numeric | 242 | 1.0, 2.0, 3.0, 4.0, 5.0 |
| `gps_lon` | Household longitude (WGS84) - RESTRICTED | numeric | 1115 | not shown |
| `gps_lat` | Household latitude (WGS84) - RESTRICTED | numeric | 1115 | not shown |
| `gps_flag` | GPS point >5 km from community median (1 = flagged, retained) | numeric | 1200 | 0, 1, 2, 3, 4, 5 |
| `blackflies` | Black flies present in community (5 categories; 98 = do not know) | numeric | 1200 | 1.0, 2.0, 3.0, 4.0, 5.0, 98.0 |
| `blackflies_yes` | Perceived black flies (1 = "yes, a bit" or "yes, definitely") | numeric | 1191 | 0.0, 1.0 |
| `blackfly_season` | Season black flies noticed (Round 3): wet, dry, all year | numeric | 400 | 1.0, 2.0, 3.0 |
| `blackfly_time` | Time of day black flies noticed (Round 3) | numeric | 400 | 1.0, 2.0, 3.0, 4.0 |
| `fast_river` | Fast-flowing river in or near community (Round 3) | numeric | 400 | 0.0, 1.0 |
| `river_dries` | River dries in the dry season (Round 3) | numeric | 400 | 0.0, 1.0, 98.0 |
| `river_activity` | Main activity at the river (Round 3): farming, mining, sand, fishing, other | numeric | 400 | 1.0, 2.0, 3.0, 4.0, 5.0 |
| `river_dist_min` | Self-reported round-trip walking time to the river (minutes) | numeric | 1194 | 1 to 360 |
| `river_dist_grp` | Round-trip time group: 1 = <=10, 2 = 11-30, 3 = 31-60, 4 = >60 minutes | numeric | 1194 | 1.0, 2.0, 3.0, 4.0 |
| `know_flies` | Knows black flies transmit onchocerciasis (1 = yes) | numeric | 1200 | 0.0, 1.0 |
| `knowledge_score` | Onchocerciasis knowledge score | numeric | 1200 | 0.0, 1.0, 2.0, 3.0 |
| `wg_disability` | Functional disability, Washington Group short set (1 = yes) | numeric | 1200 | 0.0, 1.0 |

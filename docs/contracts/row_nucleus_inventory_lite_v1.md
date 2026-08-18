# HPFA Row Nucleus Inventory Lite V1

## Amaç

Visible CSV/XML row evidence'ını match-local, same-role `row nucleus candidate` nesnelerine bağlar.

Bu katman event veya physical action üretmez.

```text
row_nucleus_candidate != canonical_event
row_nucleus_candidate != physical_action_truth
row_nucleus_candidate != action_bundle
row_nucleus_candidate != validated_identity
```

## Upstream

Current producer:

`triangulated_event_reflection_resolver_lite_v1`

Row Nucleus, mevcut resolver'ın CSV/XML parsing ve visible-field normalization davranışını yeniden icat etmez. Aynı current product primitive'lerini tüketir.

XLSX row identity üretmez; aggregate/reconciliation support yüzeyi olarak kalır.

## Candidate key

Same-role grouping key:

```text
source_role + provider_row_id_candidate
```

`provider_row_id_candidate` sayısal canonicalization görmez. Örneğin `001` ile `1` aynı candidate kimlik değildir.

Provider row ID validated event/player/team identity değildir.

## Role projection

```text
PLAYER      -> PLAYER_ACTOR_CANDIDATE
GOALKEEPER  -> GOALKEEPER_REACTION_ACTOR_CANDIDATE
TEAM        -> TEAM_CONTEXT_CANDIDATE
```

Cross-role fusion bu katmanda yasaktır.

## Serialization lineage

Aynı role ve provider-row ID candidate içinde:

```text
REFLECTION_CANDIDATE_EXACT
REFLECTION_CANDIDATE_DISCREPANCY
REFLECTION_CANDIDATE_UNRESOLVED
```

Exact visible-field equality bile `same_upstream_origin_truth` veya physical-action truth açmaz.

Tüm nuclei için:

```text
independence_status=INDEPENDENCE_UNRESOLVED
independent_source_vote_allowed=false
```

Discrepancy veya incomplete pairing:

```text
lineage_admission_status=LINEAGE_REVIEW_REQUIRED
```

## Visible fields

Candidate support fields:

```text
start
end
code
team
action
half
pos_x
pos_y
```

`start/end` yalnız source-timeline evidence'dır. Physical action onset/duration değildir.

Aynı anchor üzerinde farklı provider-row ID ve semantic label taşıyan rows bu katmanda birleştirilmez. Multi-label on-ball action bundling sonraki katmandır.

## Coordinate policy

Current reconstructed version explicit reviewed semantic-role producer taşımadığı için koordinat muafiyeti tahmin etmez.

Coordinate unresolved nucleus:

```text
REVIEW_REQUIRED
```

#228'de kanıtlanmış admin exemption davranışı ancak explicit `ADMIN_ONLY` + reviewed administrative semantic role upstream bağlandığında yeniden açılabilir.

## Duplicate policy

Exact same-content reflection paths current resolver tarafından bir kez parse edilir; duplicate reflection lineage kaydı korunur. Duplicate path row/nucleus volume'u ikinci kez artırmaz.

## G01-G18 compatibility rollup

Bu node yalnız gerçekten gözleyebildiği gate'leri değerlendirir. Downstream semantic/action/event gates `NOT_APPLICABLE` kalabilir; bilinmeyen truth için PASS üretilmez.

Özellikle:

- G07 coordinate surface eligibility
- G09 serialization lineage readiness
- G15 XLSX identity exclusion
- G17 canonical event admission = NOT_APPLICABLE
- G18 claim release = NOT_APPLICABLE

## Claim ceiling

Always:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
deduplicated_event_count=UNKNOWN
row_nucleus_is_canonical_event=false
physical_action_identity_truth=false
same_upstream_origin_truth=false
validated_event_identity=false
validated_team_identity=false
validated_player_identity=false
independent_source_vote_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
comparison_allowed=false
claim_allowed=false
production_release=false
```

## Required regressions

- provider ID textual representation preserved (`001` != `1`)
- exact duplicate reflection not double-counted
- visible-field discrepancy propagates REVIEW_REQUIRED
- TEAM projects to context, not actor
- same-anchor multi-label rows remain separate before bundling
- missing coordinate remains REVIEW_REQUIRED without explicit admin exemption
- XLSX excluded from row identity
- `test_no_sample_match_identity_leak`

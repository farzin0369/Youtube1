# BAMO Autonomy — honest charter

## Goal
Build the strongest practical autonomous motion-graphics engine possible on this repo:
Python + Blender CPU + FFmpeg + local/cloud LLM + self-heal rules.

## What exists today
- AI Scene Director (scene graphs from narration)
- Blender CPU cinematic camera (Catmull-Rom, DOF, bloom)
- Self-heal + **auto-learning heal rules** (`app/bamo_heal_rules.json`)
- 11-agent editorial council (`app/bamo_agent_council.py`)
- Autopilot decision cycle (`app/bamo_autopilot.py`)
- YouTube client (upload only when operator enables gates)

## What does not exist
- Superhuman general intelligence
- Guaranteed path to millions of subscribers
- Unrestricted self-rewriting of the entire codebase by the model

## Autonomy levels
1. **Heal** — detect/repair known breakage, learn safe rules
2. **Produce** — generate real 3D previews continuously
3. **Judge** — score hook/SEO/retention via council or local policy
4. **Publish** — optional; requires `BAMO_AUTOPILOT_PUBLISH=true` and `BAMO_PRODUCTION_VISUALS_APPROVED=true`
5. **Grow** — iterative packaging improvement from scores (not magic growth)

## Operator switches
| Env | Effect |
|-----|--------|
| `BAMO_AUTOPILOT_PUBLISH` | Allow publish step in autopilot |
| `BAMO_PRODUCTION_VISUALS_APPROVED` | Human visual approval gate |
| `BAMO_AUTOPILOT_COMMIT_HEALS` | Commit heal rule promotions |

## How to run one cycle
```bash
python scripts/bamo_autopilot_cycle.py
```

## Growth reality
Millions of followers come from consistent high-quality unique videos, packaging, and audience fit.
Autopilot can increase *throughput and consistency*; it cannot invent guaranteed virality.

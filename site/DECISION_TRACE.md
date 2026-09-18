# Decision Trace — RIS site taste pass

## Identity
Editorial Web Designer + Product UI (conversion page for judges/campus)

## Grounding
Junior-designer assumption: CRIW pitch + pilot LOI page; offline constraint is the story; keep clay/glass/physics as signature but strip SaaS median patterns.

## Traces

```json
[
  {
    "decision": "No AI-detection skill exists; apply design-blueprint anti-slop + frontend-design taste",
    "reason": "Desktop skill store has no anti-AI-detection tool; closest are anti-slop and taste design skills",
    "alternatives": ["invent fake anti-AI skill", "leave site unchanged"],
    "tradeoff": "Does not help evade detectors; only de-templates visual design"
  },
  {
    "decision": "Write DESIGN.md as taste layer before more site edits",
    "reason": "design-blueprint requires a durable spec so later 'make it crazier' requests don't reintroduce slop",
    "alternatives": ["edit HTML ad hoc"],
    "tradeoff": "Extra file to maintain"
  },
  {
    "decision": "Remove 4-up stat card grid (U5)",
    "reason": "Floating 0/1/12/200 cards are the SaaS median; numbers belong in prose with ports",
    "alternatives": ["keep stats with different icons"],
    "tradeoff": "Less scannable at a glance for skimmers"
  },
  {
    "decision": "Convert 6-card feature grid to numbered README list (W5/U2)",
    "reason": "Icon+title+two-line grid is the strongest web slop tell; stations read better as protocol",
    "alternatives": ["asymmetric masonry cards"],
    "tradeoff": "Fewer 'product marketing' visual blocks"
  },
  {
    "decision": "One filled CTA per viewport (U6)",
    "reason": "Hierarchy: Pilot is primary; plan/one-pager/app become text links",
    "alternatives": ["three equal ghost+fill buttons"],
    "tradeoff": "App link is quieter on sticky bar"
  },
  {
    "decision": "Sharpen hero lede (U7)",
    "reason": "Name model, ports, no-API-key instead of 'physics that actually move'",
    "alternatives": ["keep hype line"],
    "tradeoff": "Slightly less 'wow' copy"
  },
  {
    "decision": "Keep oil WebGL + clay + springs as signature",
    "reason": "User asked for physics/3D/clay/glass; anti-slop does not ban motion, only median layouts",
    "alternatives": ["flat editorial page only"],
    "tradeoff": "Heavier first paint; reduced-motion still required"
  }
]
```

## Anti-slop self-check
flagged: U5 stat trios → proof strip with real ports  
flagged: W5 feature grid → stations-readme list  
flagged: U6 button soup → one filled Pilot CTA  
flagged: U7 vague hero copy → specific product sentence  
U1 oil field kept with Decision Trace (not purple-blue-cyan SaaS gradient)

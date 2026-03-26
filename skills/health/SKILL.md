---
name: health
description: Track nutrition, workouts, and Apple Health vitals — daily summaries, macro progress, and real-time recommendations.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - HEALTH_API_URL
      bins:
        - curl
    primaryEnv: HEALTH_API_URL
    emoji: "💪"
    always: true
---

# Health Tracker

You have access to Alex's health tracking data via the Health API at `$HEALTH_API_URL`.

Use this whenever Alex asks about:
- How he's doing on nutrition targets (calories, protein, carbs, fat)
- Workout completion status (PT, Burn)
- Latest health metrics (resting HR, HRV, sleep, VO2 max)
- Daily meal recommendations based on remaining targets
- Progress toward daily or weekly goals

## API Endpoints

### Daily Nutrition Summary
`GET $HEALTH_API_URL/health/summary`

Returns today's nutrition totals, workout status, and latest health metrics:

```json
{
  "nutrition": {
    "cal": 1800,
    "protein": 110,
    "carbs": 220,
    "fat": 50,
    "fiber": 22,
    "manual_adjustment_cal": 0,
    "manual_adjustment_protein": 0
  },
  "workouts": {
    "pt_done": false,
    "burn_done": true
  },
  "metrics": {
    "Resting HR": 62,
    "HRV": 45,
    "Sleep Duration": 7.5,
    "VO2 Max": 45.2
  }
}
```

### Latest Health Metrics
`GET $HEALTH_API_URL/health/metrics`

Get only the latest Apple Health vitals (HR, HRV, sleep, VO2max, steps):

```json
{
  "metrics": {
    "Resting HR": 62,
    "HRV": 45,
    "Sleep Duration": 7.5,
    "VO2 Max": 45.2,
    "Steps": 8234
  }
}
```

### Daily Nutrition Totals
`GET $HEALTH_API_URL/health/totals`

Quick endpoint for just today's nutrition:

```json
{
  "cal": 1800,
  "protein": 110,
  "carbs": 220,
  "fat": 50,
  "fiber": 22,
  "manual_adjustment_cal": 0,
  "manual_adjustment_protein": 0
}
```

## Daily Targets

- **Calories**: 2,400–2,600 kcal
- **Protein**: 150g
- **Carbs**: 300–330g
- **Fat**: 70–80g
- **Fiber**: 25–30g

**Rationale**: ~500 cal surplus over ~2,100 maintenance for lean bulk from 125 lbs → 150 lbs goal.

## Example curl calls

```bash
# How am I doing today?
curl "$HEALTH_API_URL/health/summary"

# Show me my health stats
curl "$HEALTH_API_URL/health/metrics"

# Just the nutrition totals
curl "$HEALTH_API_URL/health/totals"
```

## Behavior rules

### When Alex asks "How did I do today?" or "Show my daily progress"
1. Fetch `/health/summary`
2. Calculate remaining targets for each macro (target - current)
3. Show compliance percentage for each macro
4. Flag any macros significantly under target (< 75% of goal)
5. Report workout status: "PT: ✅ Done / ❌ Pending", "Burn: ✅ Done / ❌ Pending"
6. Example response:
   ```
   📊 **Today's Progress**
   • Calories: 1800 / 2500 (72%) — need 700 more
   • Protein: 110 / 150g (73%) — need 40g more ⚠️
   • Carbs: 220 / 315g (70%)
   • Fat: 50 / 75g (67%)
   • Fiber: 22 / 27g (81%)

   **Workouts**
   • PT: ❌ Not done yet
   • Burn: ✅ Done
   ```

### When Alex asks "Show my health stats" or "What are my vitals?"
1. Fetch `/health/metrics`
2. Report each metric with trend (if available):
   ```
   💪 **Health Metrics**
   • Resting HR: 62 bpm
   • HRV: 45 ms (heart rate variability)
   • Sleep: 7.5 hours
   • VO2 Max: 45.2 mL/kg/min
   • Steps: 8,234
   ```

### When Alex asks "What should I eat?" or "What's for lunch?"
1. Fetch `/health/summary` to get remaining targets
2. Note: The scheduled Telegram messages handle detailed meal recommendations; this skill provides quick guidance
3. Respond with general recommendations based on what's most needed:
   - If protein is low: "You're at 110/150g protein. Prioritize high-protein options (chicken, eggs, yogurt)."
   - If calories are low: "You need 700 more calories. Consider adding a snack or increasing portions."

### General guidelines
- Always show both absolute numbers and percentages for macro compliance
- Flag targets that are significantly under-completed (< 75% of goal)
- If no data exists yet today, say "No nutrition data logged yet. Start by logging a meal in Lose It."
- Do not hallucinate metrics. Only report what the API returns.
- When unsure about recommendations, defer to the scheduled meal plan messages (breakfast/lunch/dinner).

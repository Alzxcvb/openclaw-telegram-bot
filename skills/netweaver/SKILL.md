---
name: netweaver
description: Query your personal contacts database (NetWeaver) — find contacts by location, tag, date, or overdue follow-up status.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - NETWEAVER_API_URL
      bins:
        - curl
    primaryEnv: NETWEAVER_API_URL
    emoji: "🕸️"
    always: true
---

# NetWeaver Contacts

You have access to Alex's personal contacts database via the NetWeaver API at `$NETWEAVER_API_URL`.

Use this whenever Alex asks about:
- Who he knows in a specific city or country
- Contacts with a specific tag (veteran, friend, work, family, etc.)
- Who has a birthday on a specific date
- Contacts he hasn't reached out to in a while (overdue)
- Travel planning — who to reach out to before visiting somewhere

## API Endpoint

`GET $NETWEAVER_API_URL/api/query`

All parameters are optional and combinable:

| Parameter | Example | What it does |
|-----------|---------|--------------|
| `city` | `?city=Berlin` | Contacts based in that city |
| `country` | `?country=Germany` | Contacts in that country |
| `tag` | `?tag=veteran` | Contacts with that tag |
| `date` | `?date=11-11` | Contacts matched by follow-up rules on MM-DD |
| `birthday` | `?birthday=03-15` or `?birthday=today` | Contacts with that birthday |
| `overdue` | `?overdue=true` | Contacts past their follow-up interval |
| `search` | `?search=John` | Search by name, email, or tag |

## Response format

```json
{
  "count": 3,
  "contacts": [
    {
      "name": "Jane Smith",
      "email": "jane@example.com",
      "city": "Berlin",
      "country": "Germany",
      "tags": ["friend", "work"],
      "birthday": "03-15",
      "lastInteraction": "2025-11-10T00:00:00Z",
      "followUpInterval": 30,
      "socialLinks": [{ "platform": "instagram", "handle": "@janesmith" }]
    }
  ]
}
```

## Example curl calls

```bash
# Who does Alex know in Berlin?
curl "$NETWEAVER_API_URL/api/query?city=Berlin"

# List all veterans (for Veterans Day Nov 11)
curl "$NETWEAVER_API_URL/api/query?tag=veteran"

# Who needs a follow-up today based on Nov 11 rules?
curl "$NETWEAVER_API_URL/api/query?date=11-11"

# Overdue contacts
curl "$NETWEAVER_API_URL/api/query?overdue=true"

# Birthday contacts today
curl "$NETWEAVER_API_URL/api/query?birthday=today"
```

## Behavior rules

- When Alex says "I'm heading to [city]" or "planning to visit [country]" → query by city/country and list any contacts there. Offer to help him reach out.
- When Alex asks about a holiday (Veterans Day, Hanukkah, etc.) → query `?date=<MM-DD>` AND `?tag=<relevant tag>` and combine results.
- When Alex asks "who should I catch up with?" → query `?overdue=true`.
- Always present contacts in a clean, scannable list with name, location, and primary social link if available.
- If count is 0, say so clearly and suggest adding contacts via the NetWeaver web app.
- Do not hallucinate contact info. Only report what the API returns.

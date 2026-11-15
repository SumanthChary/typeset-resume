# resume.json schema

Sections are an **ordered list**, so reorder, add and delete freely. See `examples/sample-resume.json` for a complete valid file.

```json
{
  "basics": {
    "name": "Full Name",
    "headline": "Role | Specialty",
    "location": "City, Country",
    "email": "name@example.com",
    "phone": "+00 00000 00000",
    "links": [{"label": "github.com/name", "url": "github.com/name"}]
  },
  "summary": "Two to three plain sentences. Optional.",
  "summary_title": "Summary",
  "sections": [ ...see types below... ]
}
```

## Section types

| type | fields |
|---|---|
| `experience` | `title`, `items[]`: `role`, `org`, `dates`, `location`, `bullets[]` |
| `education` | `title`, `items[]`: `org`, `degree`, `dates`, `location`, `details[]` (coursework, honours) |
| `projects` | `title`, `items[]`: `name`, `tagline`, `link`, `dates`, `bullets[]` |
| `skills` | `title`, `groups[]`: `label`, `items` (comma separated string) |
| `list` | `title`, `bullets[]` (achievements, awards, writing, volunteering, certifications) |
| `text` | `title`, `text` (a single paragraph) |

## Formatting rules

- Inline markdown allowed in any text: `**bold**` for the one or two proof words in a bullet (a product name or a number), `*italic*` rarely.
- Dates: `Mon YYYY – Mon YYYY` or `YYYY – Present`. Use one format everywhere.
- Straight quotes and `--` are converted to curly quotes and en dashes by the renderer.
- Never leave placeholders. `check_resume.py` blocks `[add number]`, `TODO` and similar.
- Links: `url` may omit `https://`. Emails become `mailto:` links.

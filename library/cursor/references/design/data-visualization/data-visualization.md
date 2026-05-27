# Data Visualization Principles

Every chart makes exactly one argument. If it needs a paragraph of explanation, redesign it.

## Chart Selection

| Your question is... | Use... | Avoid... |
|---|---|---|
| How does X change over time? | Line chart | Pie chart |
| How do categories compare? | Bar chart (horizontal for many categories) | 3D charts |
| What is the distribution? | Histogram, box plot | Bar chart (misrepresents distribution) |
| What is the relationship between X and Y? | Scatter plot | Line chart (implies continuity) |
| What is the composition? | Stacked bar, treemap | Pie chart (if >5 categories) |
| What is the geographic pattern? | Choropleth or bubble map | Tables |
| How does one part relate to the whole? | Pie chart (max 5 slices), waffle chart | Pie chart with >7 slices |

## Color for Data

### Palette Types
- **Sequential**: low-to-high values. Single hue, varying lightness. Use for magnitude (counts, percentages, temperature).
- **Diverging**: values above and below a meaningful center. Two hues with neutral midpoint. Use for deviation (profit/loss, above/below average).
- **Categorical**: distinct groups with no order. Use distinct hues. Maximum 7-8 categories before it becomes unreadable.

### Accessibility
- Test all palettes with a color-blindness simulator (protanopia, deuteranopia)
- Never use red/green as the only distinguishing factor
- Use shape, pattern, or label in addition to color
- Provide alt text for all charts describing the key finding, not just "a bar chart"

## Dashboard Layout

- **Information hierarchy**: most important metric at top-left (where eyes start)
- **Progressive disclosure**: overview first, then drill-down on demand
- **One question per chart**: don't overload a single visualization
- **Consistent time axis**: if multiple charts show time, align the x-axis
- **Annotations**: mark significant events directly on the chart (policy changes, outages, seasonal events)

## Labeling and Annotation

- Direct labeling on data points beats legends (less eye movement)
- Title states the finding, not the chart type: "Revenue grew 23% in Q3" not "Revenue by Quarter"
- Source and date always visible
- Units always labeled on axes

## Common Lies to Avoid

- **Truncated y-axis**: starting at non-zero exaggerates differences. Always start at 0 for bar charts.
- **Dual y-axes**: two different scales on the same chart mislead about correlation. Use two separate charts.
- **Cherry-picked time ranges**: choosing start/end dates that support a narrative
- **3D effects**: distort perception of values. Never use 3D charts.
- **Pie charts for comparison**: humans are bad at comparing angles. Use bar charts for comparison.
- **Unlabeled axes**: a chart without units is meaningless

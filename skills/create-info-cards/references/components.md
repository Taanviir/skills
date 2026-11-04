# Card components

This file holds the markup for the components that `assets/template.html` styles. Each one goes inside `.card-body`. The heights are rough figures at full scale, and they help you plan a card before the fit check. The body has about 1,100px to fill.

| Component | Use it for | Height |
|---|---|---|
| `h2` and `.eyebrow` | every card | 170 to 260px |
| `.lede` | a setup of 1 to 3 sentences | 55px per line |
| `.stats` | 4 headline numbers on the cover | about 500px |
| `.tl` | a dated sequence of 4 to 6 rows | 90 to 130px per row |
| `.steps` | a real process of 3 to 5 steps | 50 to 95px per step |
| `.pts` | 3 or 4 claims, each with a bold lead-in | 95 to 140px per item |
| `.quote` and `.who` | one line the speaker actually said | 70px per line |
| `.compare` | two sides of a contrast, or a callout box with `.compare.one` | 250 to 330px |
| `.bars` | an escalation or a ranking of 3 to 5 bars | 200px |

```html
<div class="stats">
  <div class="stat"><span class="n">100+</span><span class="l">label</span></div>
  <!-- exactly 4 -->
</div>

<ol class="tl">
  <li><span class="d">Feb 2026</span><span class="t">What happened.</span></li>
</ol>

<!-- Wrap each step's text in a span. The li is a grid, so loose inline elements become grid cells. -->
<ol class="steps">
  <li><span>Step text with an optional <span class="chip">chip</span></span></li>
</ol>

<ul class="pts">
  <li><b>Lead-in.</b> The rest of the point.</li>
</ul>

<p class="quote">Exact words from the source.</p>
<div class="who">Speaker name</div>

<div class="compare">
  <div><span class="tag">Side A</span><h3>Short head</h3><p>One or two sentences.</p></div>
  <div><span class="tag">Side B</span><h3>Short head</h3><p>One or two sentences.</p></div>
</div>

<div class="bars">
  <div style="height:40%">small</div>
  <div style="height:70%">bigger</div>
  <div style="height:100%">biggest</div>
</div>

<div class="spacer"></div>  <!-- pushes what follows to the card bottom -->
```

Restyle any of these to fit the topic's world. Add a new component when the content has a shape none of these fit, such as a map, a recipe ratio or a scoreboard. Size a new component in px at full scale, and give it a fixed or content-driven height so the fit check can measure it.

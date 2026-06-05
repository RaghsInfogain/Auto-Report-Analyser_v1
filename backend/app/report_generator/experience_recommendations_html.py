"""Shared recommendations tab HTML for editorial reports (JMeter combined load, Web Vitals, Lighthouse)."""
from __future__ import annotations


def recommendations_panel_html(title_line: str, *, report_context: str = "jmeter") -> str:
    """
    Full <div id=\"panel-recommendations\" ...> block. title_line must already be HTML-escaped.

    report_context:
      - \"jmeter\": copy tuned for load-test / JTL reports
      - \"web_vitals\": Lighthouse / CSV Web Vitals (neutral wording)
    """
    is_wv = report_context == "web_vitals"
    prog_intro = (
        "Organisational and engineering practices that complement the <strong>{tl}</strong> results in this report. "
        "The first part covers cadence, governance, and charters; the second links those commitments to concrete "
        "product optimisation (Core Web Vitals, stack changes, monitoring)."
    )
    if is_wv:
        prog_intro = (
            "Organisational and engineering practices that complement the <strong>{tl}</strong> Web Vitals and "
            "lab-style signals in this report. The first part covers cadence, governance, and charters; the second "
            "links those commitments to concrete front-end and platform optimisation."
        )

    app_opt_intro = (
        "These recommendations frame industry best practices for <strong>{tl}</strong> in light of this load test — "
        "end-to-end response times, concurrency bands, error patterns, and capacity envelopes shown in the other tabs. "
        "They complement (not replace) findings under Root Cause and Capacity."
    )
    if is_wv:
        app_opt_intro = (
            "These recommendations frame industry best practices for <strong>{tl}</strong> in light of this Lighthouse "
            "/ Web Vitals assessment — paint metrics, stability, and interactivity shown in the other tabs. "
            "They complement (not replace) findings under Issues and Roadmap."
        )

    ttfb_note = (
        "Time from request until the first response byte. High TTFB aligns with slow origin, queuing, or cold routes — "
        "cross-check with the Latency decomposition table in this report."
    )
    if is_wv:
        ttfb_note = (
            "Time from request until the first response byte. High TTFB aligns with slow origin, queuing, or cold "
            "routes — compare with per-page server timing in the Detailed metrics tab."
        )

    server_blurb = (
        "Items below directly influence mean and tail latency seen in this JTL and in the transaction percentile table."
    )
    if is_wv:
        server_blurb = (
            "Items below directly influence LCP, responsiveness, and stability for the pages and URLs in this report."
        )

    evidence_footer = (
        "Figures vary by product; treat as directional. Re-measure {tl} after each change using the same scenarios as this test."
    )
    if is_wv:
        evidence_footer = (
            "Figures vary by product; treat as directional. Re-measure {tl} after each change using the same URLs and "
            "test profiles where possible."
        )

    closing = (
        "Performance is a continuous loop: monitor → hypothesise → change → re-test. Pair these recommendations with "
        "the evidence in the Scorecard, Response Time, and Root Cause tabs to build a short, ordered backlog for {tl}."
    )
    if is_wv:
        closing = (
            "Performance is a continuous loop: monitor → hypothesise → change → re-test. Pair these recommendations with "
            "the evidence in the Overview, Issues, and Roadmap tabs to build a short, ordered backlog for {tl}."
        )

    cadence_note = (
        "Adjust frequencies to your release tempo; keep <strong>end-to-end load</strong> and <strong>stress/soak</strong> "
        "on the path to production for systems like <strong>{tl}</strong>."
    )
    if is_wv:
        cadence_note = (
            "Adjust frequencies to your release tempo; keep <strong>synthetic audits</strong>, "
            "<strong>RUM validation</strong>, and <strong>real-device checks</strong> on the path to production for "
            "experiences like <strong>{tl}</strong>."
        )

    tl = title_line

    if not is_wv:
        server_rows = f"""
        <tr><td class="row-label">Database</td><td>Indexing, query tuning, connection pooling; watch saturation if errors rose with VU.</td></tr>
        <tr><td class="row-label">APIs</td><td>Compress JSON (gzip/Brotli), paginate large payloads, consider GraphQL or field filtering where chatty.</td></tr>
        <tr><td class="row-label">Caching</td><td>Redis/Memcached (or equivalent) for hot reads and rendered fragments aligned to {tl} traffic patterns.</td></tr>
        <tr><td class="row-label">Infrastructure</td><td>Horizontal scale, load balancing, regions near your user base; align auto-scale with proven-safe VU from this report.</td></tr>"""
    else:
        server_rows = f"""
        <tr><td class="row-label">Database</td><td>Indexing, query tuning, connection pooling; watch saturation if errors rose with load.</td></tr>
        <tr><td class="row-label">APIs</td><td>Compress JSON (gzip/Brotli), paginate large payloads, consider GraphQL or field filtering where chatty.</td></tr>
        <tr><td class="row-label">Caching</td><td>Redis/Memcached (or equivalent) for hot reads and rendered fragments aligned to {tl} traffic patterns.</td></tr>
        <tr><td class="row-label">Infrastructure</td><td>Horizontal scale, load balancing, regions near your user base; align auto-scale with observed peaks in production.</td></tr>"""

    strat_lede = (
        "One-off load tests rarely match production reality. A continuous discipline reduces surprise incidents and keeps "
        f"<strong>{tl}</strong> shippable as traffic and code change."
    )
    if is_wv:
        strat_lede = (
            "One-off audits rarely match production reality. A continuous discipline reduces surprise incidents and keeps "
            f"<strong>{tl}</strong> shippable as traffic and code change."
        )

    strat_b4 = (
        "<li>Demonstrates whether the system can sustain <strong>expected and peak</strong> load profiles.</li>"
        "<li>Produces evidence for scaling, capacity, and investment decisions (aligned with capacity figures in this report).</li>"
    )
    if is_wv:
        strat_b4 = (
            "<li>Demonstrates whether the experience can sustain <strong>expected and peak</strong> traffic profiles.</li>"
            "<li>Produces evidence for scaling, capacity, and investment decisions.</li>"
        )

    return f"""
<div id="panel-recommendations" class="panel">
<div class="page">
  <div class="section">
    <div class="section-label">Performance programme</div>
    <h2 class="section-title">Performance testing recommendations</h2>
    <p class="section-desc">{prog_intro.format(tl=tl)}</p>
  </div>

  <div class="section">
    <div class="section-label">1 · Strategy</div>
    <h3 class="section-title" style="font-size:1.15rem">Why performance testing must be continuous</h3>
    <p class="section-desc">{strat_lede}</p>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li>Surfaces bottlenecks <strong>early</strong> in the lifecycle — cheaper to fix before release.</li>
      <li>Lowers the risk of performance-related incidents after go-live.</li>
      {strat_b4}
    </ul>
  </div>


  <div class="section">
    <div class="section-label">2 · Triggers</div>
    <h3 class="section-title" style="font-size:1.15rem">Mandatory performance testing triggers</h3>
    <p class="section-desc">Treat a full performance cycle as <strong>non-optional</strong> when any of the following apply to <strong>{tl}</strong> or its dependencies.</p>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li><strong>Major release</strong> — material features, core behaviour changes, or UI / architecture shifts.</li>
      <li><strong>Infrastructure changes</strong> — hardware, network, cloud region, or platform upgrades.</li>
      <li><strong>Third-party integrations</strong> — new external APIs, payments, identity, or data partners on critical paths.</li>
      <li><strong>High-traffic events</strong> — campaigns, launches, or seasonal peaks; validate headroom before demand arrives.</li>
    </ul>
  </div>

  <div class="section">
    <div class="section-label">3 · Cadence</div>
    <h3 class="section-title" style="font-size:1.15rem">Recommended testing cadence</h3>
    <p class="section-desc">{cadence_note.format(tl=tl)}</p>
    <div class="rec-cadence-wrap">
    <table class="data-table">
      <thead><tr><th>Test type</th><th>Frequency</th><th>Environment</th><th>Objective</th><th>Outcome</th></tr></thead>
      <tbody>
        <tr><td class="row-label">Unit performance</td><td>Every build</td><td>Dev / CI</td><td>Catch regressions early</td><td>Pass/fail on the build</td></tr>
        <tr><td class="row-label">Component / API</td><td>Daily / per sprint</td><td>QA / staging</td><td>Validate services in isolation</td><td>Baselines &amp; trends</td></tr>
        <tr><td class="row-label">End-to-end load</td><td>Weekly / pre-release</td><td>Staging / pre-prod</td><td>System under expected load</td><td>Performance sign-off</td></tr>
        <tr><td class="row-label">Stress / soak</td><td>Monthly / major release</td><td>Staging / pre-prod</td><td>Breaking points &amp; stability</td><td>Capacity &amp; stability report</td></tr>
        <tr><td class="row-label">Scalability</td><td>Quarterly / major release</td><td>Staging / pre-prod</td><td>Scaling behaviour &amp; limits</td><td>Scaling strategy document</td></tr>
        <tr><td class="row-label">Chaos / resiliency</td><td>Quarterly / major release</td><td>Staging / pre-prod</td><td>Failure handling &amp; recovery</td><td>Resiliency report</td></tr>
      </tbody>
    </table>
    </div>
  </div>

  <div class="section">
    <div class="section-label">4 · Risk</div>
    <h3 class="section-title" style="font-size:1.15rem">The business cost of skipping performance tests</h3>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li><strong>Revenue</strong> — slow pages and outages directly reduce conversion and transactions.</li>
      <li><strong>Reputation</strong> — poor experience erodes trust and NPS.</li>
      <li><strong>Cost</strong> — emergency fixes, war rooms, and late scaling are more expensive than planned testing.</li>
      <li><strong>SLA</strong> — contractual penalties when availability or latency commitments are missed.</li>
      <li><strong>Churn</strong> — users move to faster alternatives when performance is visibly worse than competitors.</li>
    </ul>
  </div>

  <div class="section">
    <div class="section-label">5 · Maturity</div>
    <h3 class="section-title" style="font-size:1.15rem">Performance testing maturity model</h3>
    <div class="rec-maturity">
      <div class="rec-card"><h4>Level 1 · Reactive &amp; ad-hoc</h4><ul><li>Testing mainly after incidents or complaints.</li><li>Limited tooling, no standard workload models.</li><li>Little shared visibility into trends for <strong>{tl}</strong>.</li></ul></div>
      <div class="rec-card"><h4>Level 2 · Proactive &amp; integrated</h4><ul><li>Testing embedded in planning, sprints, and release gates.</li><li>Standard tools, environments, and baselines.</li><li>Clear dashboards and ownership; this report style of evidence becomes routine.</li></ul></div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">6 · Governance</div>
    <h3 class="section-title" style="font-size:1.15rem">Governance structure and ownership</h3>
    <div class="rec-cards">
      <div class="rec-card"><h4>Executive sponsor</h4><ul><li>Budget and escalation path.</li><li>Alignment of performance goals with business outcomes.</li></ul></div>
      <div class="rec-card"><h4>Performance lead</h4><ul><li>Strategy, tool chain, and quality bar for tests.</li><li>Oversight of schedules, environments, and reporting.</li></ul></div>
      <div class="rec-card"><h4>DevOps / SRE</h4><ul><li>Test environments, observability, and pipeline hooks.</li><li>Partnership on capacity and tuning after tests.</li></ul></div>
      <div class="rec-card"><h4>Product owner</h4><ul><li>Non-functional requirements and prioritisation.</li><li>Trade-offs when performance competes with scope and dates.</li></ul></div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">7 · RACI-style</div>
    <h3 class="section-title" style="font-size:1.15rem">Roles and responsibilities</h3>
    <div class="rec-cadence-wrap">
    <table class="data-table">
      <thead><tr><th>Role</th><th>Responsibilities</th></tr></thead>
      <tbody>
        <tr><td class="row-label">Performance engineer</td><td>Design and execute tests; analyse results; recommend fixes and re-tests for <strong>{tl}</strong>.</td></tr>
        <tr><td class="row-label">Developer</td><td>Optimise code and configuration; remediate bottlenecks; participate in test design where needed.</td></tr>
        <tr><td class="row-label">QA engineer</td><td>Integrate performance cases into overall quality strategy; execute agreed scenarios.</td></tr>
        <tr><td class="row-label">SRE / DevOps</td><td>Provision environments; wire monitoring and tooling; support analysis and rollout of mitigations.</td></tr>
        <tr><td class="row-label">Product owner</td><td>Define targets and user journeys; ensure performance work is visible in the backlog.</td></tr>
        <tr><td class="row-label">Executive sponsor</td><td>Champion investment; remove blockers; accept residual risk when sign-off is required.</td></tr>
      </tbody>
    </table>
    </div>
  </div>

  <div class="section">
    <div class="section-label">8 · Charter</div>
    <h3 class="section-title" style="font-size:1.15rem">Performance test charter — what to commit to in writing</h3>
    <p class="section-desc">Capture the following for every material test cycle so stakeholders share the same definition of success for <strong>{tl}</strong>.</p>
    <div class="rec-cadence-wrap">
    <table class="data-table">
      <thead><tr><th>Element</th><th>What to document</th></tr></thead>
      <tbody>
        <tr><td class="row-label">Objective</td><td>Clear goals (e.g. latency and throughput at defined concurrency, error budget).</td></tr>
        <tr><td class="row-label">Success criteria</td><td>Numeric gates: mean / percentiles, error %, SLA compliance links.</td></tr>
        <tr><td class="row-label">Workload model</td><td>Scenarios, transaction mix, data volume, ramp profile, think times.</td></tr>
        <tr><td class="row-label">Test environment</td><td>Hardware, topology, software versions, representativeness vs production.</td></tr>
        <tr><td class="row-label">Monitoring &amp; tools</td><td>Load tool, APM, logs, metrics dashboards used during the run.</td></tr>
        <tr><td class="row-label">Schedule</td><td>Prep, execution windows, reporting milestones, and re-test triggers.</td></tr>
        <tr><td class="row-label">Sign-off</td><td>Named approvers (engineering, product, operations) and conditions for release.</td></tr>
      </tbody>
    </table>
    </div>
  </div>

  <div class="section">
    <div class="section-label">9 · Leadership</div>
    <h3 class="section-title" style="font-size:1.15rem">Building towards business continuity — the executive message</h3>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li>Performance is a core driver of customer satisfaction and revenue retention for <strong>{tl}</strong>.</li>
      <li>Investing in testing and observability reduces downside risk and total cost of incidents.</li>
      <li>Continuous performance discipline is a competitive advantage, not overhead.</li>
      <li>Performance is a <strong>shared responsibility</strong> across product, engineering, and operations.</li>
      <li>Structured testing informs capacity planning and avoids expensive emergency scale-up.</li>
      <li>Mature performance practice signals a high-performing engineering organisation.</li>
    </ul>
  </div>

  <div class="section">
    <div class="section-label">Programme priorities</div>
    <h3 class="section-title" style="font-size:1.15rem">Recommendations — embedding performance in the organisation</h3>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li><strong>Continuous strategy</strong> — integrate performance scenarios into CI/CD so regressions surface before production for <strong>{tl}</strong>.</li>
      <li><strong>Clear goals</strong> — use specific, measurable targets (latency percentiles, error %, throughput, budgets) tied to user journeys.</li>
      <li><strong>Tools &amp; infrastructure</strong> — invest in load generation, observability, and environments that mirror production realistically.</li>
      <li><strong>Culture</strong> — train teams and make performance a shared priority alongside features.</li>
      <li><strong>Iterate the process</strong> — review cadence, charters, and gates regularly using feedback and industry practice.</li>
    </ul>
  </div>

  <div class="section">
    <div class="section-label">Application optimisation</div>
    <h2 class="section-title">Performance recommendations for modern web applications</h2>
    <p class="section-desc">{app_opt_intro.format(tl=tl)}</p>
  </div>
  <div class="section">
    <div class="section-label">Experience metrics</div>
    <h3 class="section-title" style="font-size:1.15rem">Core Web Vitals and related targets</h3>
    <p class="section-desc">Real users feel performance through paint, timing, and stability metrics. Compare lab numbers from Lighthouse and field RUM when hardening {tl}.</p>
    <div class="rec-vital-grid">
      <div class="rec-vital"><div class="rv-name">Time to first byte (TTFB)</div><div class="rv-good">Good: typically &lt; 200 ms</div><p>{ttfb_note}</p></div>
      <div class="rec-vital"><div class="rv-name">First contentful paint (FCP)</div><div class="rv-good">Good: &lt; 1.8 s</div><p>First text or image painted. Improve server timing, critical CSS, and render-blocking scripts.</p></div>
      <div class="rec-vital"><div class="rv-name">Largest contentful paint (LCP)</div><div class="rv-good">Good: &lt; 2.5 s</div><p>Largest visible image or text block. Optimise hero assets, CDN, and HTML priority hints.</p></div>
      <div class="rec-vital"><div class="rv-name">Cumulative layout shift (CLS)</div><div class="rv-good">Good: &lt; 0.1</div><p>Visual stability. Reserve space for ads, fonts, and late-loaded content.</p></div>
      <div class="rec-vital"><div class="rv-name">First input delay (FID)</div><div class="rv-good">Good: &lt; 100 ms</div><p>Responsiveness to first interaction. Reduce long tasks and main-thread JavaScript.</p></div>
      <div class="rec-vital"><div class="rv-name">Interaction to next paint (INP)</div><div class="rv-good">Good: &lt; 200 ms</div><p>Broader interaction latency metric — tune event handlers and rendering work across pages used in {tl}.</p></div>
    </div>
  </div>
  <div class="section">
    <div class="section-label">Client-side</div>
    <h3 class="section-title" style="font-size:1.15rem">Front-end optimisation</h3>
    <div class="rec-cards">
      <div class="rec-card"><h4>Resource optimisation</h4><ul><li>Minify HTML, CSS, and JS; ship modern formats (e.g. WebP/AVIF).</li><li>Lazy-load images and media below the fold.</li></ul></div>
      <div class="rec-card"><h4>Caching</h4><ul><li>Set clear cache lifetimes for static assets.</li><li>Front static assets with a CDN close to users hitting {tl}.</li></ul></div>
      <div class="rec-card"><h4>JavaScript &amp; CSS</h4><ul><li>Code-split routes; defer or async non-critical scripts.</li><li>Inline critical CSS for fastest first paint.</li></ul></div>
      <div class="rec-card"><h4>Network</h4><ul><li>Prefer HTTP/2 or HTTP/3 end-to-end.</li><li>Use DNS prefetch / preload for critical origins.</li></ul></div>
    </div>
  </div>
  <div class="section">
    <div class="section-label">Server-side</div>
    <h3 class="section-title" style="font-size:1.15rem">Back-end and platform</h3>
    <p class="section-desc">{server_blurb}</p>
    <table class="data-table">
      <thead><tr><th>Area</th><th>Recommended actions</th></tr></thead>
      <tbody>{server_rows}
      </tbody>
    </table>
  </div>
  <div class="section">
    <div class="section-label">Operations</div>
    <h3 class="section-title" style="font-size:1.15rem">Monitoring and continuous improvement</h3>
    <ul style="margin:0.5rem 0 0 1.1rem;font-size:13px;line-height:1.65;color:var(--gray)">
      <li><strong>Real user monitoring (RUM)</strong> — validate that fixes move field Core Web Vitals, not just lab tests.</li>
      <li><strong>Synthetic monitoring</strong> — Lighthouse / scheduled probes for regressions on key journeys.</li>
      <li><strong>Performance budgets</strong> — cap JS weight, image bytes, and third-party tags per release.</li>
      <li><strong>CI/CD gates</strong> — block releases when lab or RUM budgets regress vs baseline for {tl}.</li>
    </ul>
  </div>
  <div class="section">
    <div class="section-label">Evidence</div>
    <h3 class="section-title" style="font-size:1.15rem">Typical optimisation impact (illustrative)</h3>
    <table class="data-table">
      <thead><tr><th>Initiative</th><th>Example outcome</th></tr></thead>
      <tbody>
        <tr><td>Image optimisation</td><td>Often materially faster LCP; conversion lifts reported in the 10–20% range when pages were image-bound.</td></tr>
        <tr><td>CDN for static assets</td><td>Large reductions in global TTFB for cached objects.</td></tr>
        <tr><td>JavaScript code splitting</td><td>Improved responsiveness (FID/INP) when main-thread work dominated.</td></tr>
      </tbody>
    </table>
    <p class="section-desc" style="margin-top:0.75rem">{evidence_footer.format(tl=tl)}</p>
  </div>
  <div class="section">
    <div class="section-label">Summary</div>
    <h3 class="section-title" style="font-size:1.05rem">Closing note</h3>
    <p class="section-desc">{closing.format(tl=tl)}</p>
  </div>
</div></div>
"""

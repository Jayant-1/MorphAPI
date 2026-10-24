"""
Tests for DOM Pruner and structural character reduction.
"""

from backend.app.services.dom_pruner import prune_dom, calculate_pruning_ratio


SAMPLE_VERBOSE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Verbose Portal</title>
  <style>
    body { font-family: sans-serif; background: #fff; margin: 0; }
    .header { height: 60px; border-bottom: 1px solid #ccc; }
    .footer { padding: 40px; color: #888; font-size: 12px; }
    .btn:hover { background: #0056b3; }
  </style>
  <script>
    window.analytics = window.analytics || [];
    function trackPageView() { console.log("tracked"); }
    trackPageView();
    for(let i=0; i<100; i++) { /* long script content */ }
  </script>
</head>
<body>
  <!-- Navigation bar with SVG icons -->
  <header class="header">
    <svg width="24" height="24" viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
    <span class="site-title">Marketplace</span>
  </header>

  <main>
    <div class="container" id="main-content">
      <h2 class="section-title">Wholesale Prices</h2>
      <table class="data-table" id="prices-grid">
        <thead>
          <tr><th>Crop</th><th>Price</th></tr>
        </thead>
        <tbody>
          <tr class="data-row">
            <td class="crop-col" data-testid="crop-0">Wheat</td>
            <td class="rate-col" data-testid="rate-0">2400.00</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>

  <noscript><p>Please enable JavaScript to continue.</p></noscript>

  <footer class="footer">
    <script src="https://cdn.example.com/tracker.js"></script>
    <p>Copyright 2026. All rights reserved.</p>
  </footer>
</body>
</html>
"""


def test_prune_dom_strips_scripts_and_styles():
    pruned = prune_dom(SAMPLE_VERBOSE_HTML)
    assert "<script" not in pruned.lower()
    assert "<style" not in pruned.lower()
    assert "<svg" not in pruned.lower()
    assert "<noscript" not in pruned.lower()


def test_prune_dom_preserves_structural_elements():
    pruned = prune_dom(SAMPLE_VERBOSE_HTML)
    assert "Wheat" in pruned
    assert "2400.00" in pruned
    assert 'class="crop-col"' in pruned
    assert 'class="rate-col"' in pruned
    assert 'id="prices-grid"' in pruned


def test_pruning_ratio_exceeds_target():
    pruned = prune_dom(SAMPLE_VERBOSE_HTML)
    ratio = calculate_pruning_ratio(SAMPLE_VERBOSE_HTML, pruned)
    # Target is >= 60-80% reduction for typical verbose web pages
    assert ratio > 0.40
    assert len(pruned) < len(SAMPLE_VERBOSE_HTML)

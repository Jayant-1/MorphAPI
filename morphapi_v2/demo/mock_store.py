"""
Simulated Mock E-Commerce Store with Mutating UI
Used for live demonstrations of MorphAPI V2's autonomous self-healing capabilities.
Supports two layout modes:
- V1: Standard card grid layout (.product-card, .product-title, .product-price, .product-link)
- V2: Multi-row redesigned catalog layout (.catalog-entry title/link, sibling .meta-row price)
"""

PRODUCTS = [
    {
        "id": 1,
        "name": "Quantum Wireless Noise-Canceling Headphones",
        "price": "$299.99",
        "description": "Adaptive noise canceling with 40-hour battery life.",
        "link": "https://example.com/products/quantum-headphones",
    },
    {
        "id": 2,
        "name": "Ultra-Wide 34-Inch Curved Gaming Monitor",
        "price": "$649.00",
        "description": "165Hz refresh rate with 1ms response time.",
        "link": "https://example.com/products/curved-monitor-34",
    },
    {
        "id": 3,
        "name": "Ergonomic Mechanical Keyboard RGB",
        "price": "$179.50",
        "description": "Hot-swappable tactile switches and wrist cushion.",
        "link": "https://example.com/products/ergo-keyboard",
    },
    {
        "id": 4,
        "name": "4K Ultra-HD Webcam with Dual Mics",
        "price": "$129.99",
        "description": "HDR video streaming with auto-framing AI.",
        "link": "https://example.com/products/4k-webcam",
    },
    {
        "id": 5,
        "name": "Precision Laser Gaming Mouse 16000 DPI",
        "price": "$89.95",
        "description": "Ultra-lightweight honeycomb shell with braided cable.",
        "link": "https://example.com/products/laser-mouse",
    },
]

MOCK_STORE_STATE = {"mode": "v1"}


def get_current_mode() -> str:
    return MOCK_STORE_STATE["mode"]


def set_mode(mode: str):
    MOCK_STORE_STATE["mode"] = "v2" if "2" in mode else "v1"


def toggle_mode() -> str:
    MOCK_STORE_STATE["mode"] = "v2" if MOCK_STORE_STATE["mode"] == "v1" else "v1"
    return MOCK_STORE_STATE["mode"]


def render_mock_store_html(mode: str | None = None) -> str:
    current_mode = mode or MOCK_STORE_STATE["mode"]
    is_v2 = "2" in current_mode

    mode_badge = (
        '<span style="background:#ef4444;color:white;padding:4px 10px;border-radius:4px;font-weight:bold;">Layout V2: Redesigned Multi-Row UI</span>'
        if is_v2
        else '<span style="background:#10b981;color:white;padding:4px 10px;border-radius:4px;font-weight:bold;">Layout V1: Standard Card Grid</span>'
    )

    action_button = (
        '<a href="/mock-store?mode=v1" style="background:#3b82f6;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;">🔄 Reset to Layout V1</a>'
        if is_v2
        else '<a href="/mock-store?mode=v2" style="background:#ef4444;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;">🚨 Break UI / Simulate Redesign (V2)</a>'
    )

    if not is_v2:
        # Layout V1: Standard repeating card elements
        items_html = ""
        for p in PRODUCTS:
            items_html += f"""
            <div class="product-card">
                <h3 class="product-title">{p['name']}</h3>
                <div class="product-price">{p['price']}</div>
                <p class="product-desc">{p['description']}</p>
                <a class="product-link" href="{p['link']}">View Product Details &rarr;</a>
            </div>
            """
        body_content = f"""
        <div class="container">
            <h1 style="color:#0f172a;margin-bottom:8px;">Quantum Gadgets Catalog</h1>
            <p style="color:#64748b;margin-bottom:24px;">Discover the next generation of computing gear.</p>
            <div class="product-grid">
                {items_html}
            </div>
        </div>
        """
    else:
        # Layout V2: Breaking frontend redesign! Multi-row sibling table where .product-card is gone!
        rows_html = ""
        for p in PRODUCTS:
            rows_html += f"""
            <tr class="catalog-entry">
                <td class="name-col">
                    <span class="catalog-tag">Hardware</span>
                    <a href="{p['link']}">{p['name']}</a>
                </td>
            </tr>
            <tr class="meta-row">
                <td class="meta-cell">
                    <span class="pricing"><span class="amount">{p['price']}</span></span>
                    <span class="summary-text">&bull; {p['description']}</span>
                </td>
            </tr>
            <tr class="catalog-spacer" style="height:10px;"><td colspan="2"></td></tr>
            """
        body_content = f"""
        <div class="container">
            <h1 style="color:#0f172a;margin-bottom:8px;">Quantum Enterprise Catalog (V2 Redesign)</h1>
            <p style="color:#64748b;margin-bottom:24px;">All CSS classes have changed. Data is structured across sibling rows.</p>
            <table class="catalog-table">
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Quantum Gadgets - Simulated Store ({'V2' if is_v2 else 'V1'})</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; background: #f8fafc; color: #1e293b; }}
        .control-bar {{ background: #0f172a; color: white; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #334155; }}
        .container {{ max-width: 1000px; margin: 30px auto; padding: 0 20px; }}
        /* V1 Styles */
        .product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .product-card {{ background: white; border-radius: 8px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .product-title {{ margin: 0 0 10px 0; font-size: 1.15rem; color: #0f172a; }}
        .product-price {{ font-size: 1.35rem; font-weight: 700; color: #059669; margin-bottom: 8px; }}
        .product-desc {{ color: #64748b; font-size: 0.9rem; line-height: 1.4; }}
        .product-link {{ display: inline-block; margin-top: 12px; color: #2563eb; text-decoration: none; font-weight: 600; font-size: 0.95rem; }}
        /* V2 Styles */
        .catalog-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .catalog-entry {{ background: #f8fafc; }}
        .name-col {{ padding: 16px 20px 8px 20px; font-weight: 600; font-size: 1.15rem; }}
        .name-col a {{ color: #0f172a; text-decoration: none; }}
        .name-col a:hover {{ text-decoration: underline; color: #2563eb; }}
        .catalog-tag {{ display: inline-block; background: #e2e8f0; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-right: 8px; font-weight: bold; text-transform: uppercase; }}
        .meta-row {{ background: white; border-bottom: 1px solid #e2e8f0; }}
        .meta-cell {{ padding: 4px 20px 16px 20px; color: #64748b; font-size: 0.95rem; }}
        .pricing .amount {{ font-size: 1.35rem; font-weight: 700; color: #dc2626; margin-right: 8px; }}
        .summary-text {{ color: #64748b; }}
    </style>
</head>
<body>
    <div class="control-bar">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-weight:700;font-size:1.1rem;letter-spacing:-0.5px;">DEMO SIMULATION CONTROLLER</span>
            {mode_badge}
        </div>
        <div>
            {action_button}
        </div>
    </div>
    {body_content}
</body>
</html>"""

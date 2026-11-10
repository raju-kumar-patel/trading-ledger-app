# code/theme/theme.py

class Theme:
    # --- Surface Elevation (Layers) ---
    BG_ROOT        = "#0a0d14"  # Main window dark obsidian base
    BG_CARD        = "#121722"  # Panels, cards, rows
    BG_ELEVATED    = "#1a2130"  # Elevated containers & table headers
    BG_INPUT       = "#161b26"  # Input search fields & textboxes
    BG_HOVER       = "#232c3f"  # Interactive hover states

    # --- Outlines & Dividers ---
    BORDER_SUBTLE  = "#1e2638"  # Clean 1px border lines
    BORDER_LIGHT   = "#2d374d"

    # --- Financial Trading Accents ---
    GREEN_BUY      = "#00c087"  # Positive returns (Pine Green)
    GREEN_BUY_HOV  = "#009e6f"
    RED_SELL       = "#f43f5e"  # Negative returns (Rose Crimson)
    RED_SELL_HOV   = "#e11d48"
    BRAND_BLUE     = "#2563eb"  # Accent CTA Blue
    ACCENT_SKY     = "#38bdf8"  # Highlights / live status
    WARN_AMBER     = "#f59e0b"  # Settle/Pending

    # --- Typography & Content ---
    TEXT_PRIMARY   = "#f1f5f9"  # Crisp high-contrast values
    TEXT_SECONDARY = "#94a3b8"  # Labels, dates, subtitles
    TEXT_MUTED     = "#64748b"  # Watermarks & headers

    # --- Precision Geometry ---
    RADIUS_CARD    = 14         # Modern mobile card radius
    RADIUS_BTN     = 8          # Touch-friendly buttons
    RADIUS_INPUT   = 8
    PAD_PAGE       = 14

    # --- Fonts ---
    FONT_FAMILY    = "Segoe UI"
    FONT_NUMERIC   = "Consolas" # Monospace figures (no jitter)

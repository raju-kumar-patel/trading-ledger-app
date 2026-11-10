import tkinter as tk
import customtkinter as ctk
from theme.theme import Theme


class SparklineGraph(ctk.CTkFrame):
    """
    Ultra-lightweight Canvas-based 1-Week Sparkline Graph.
    - Zero external dependency (Matplotlib-free, ultra-fast rendering)
    - Auto-normalizes prices to fit canvas boundaries
    - Green line for positive 1-week return, Red for negative
    """
    def __init__(self, master, width: int = 120, height: int = 36, **kwargs):
        super().__init__(master, fg_color="transparent", width=width, height=height, **kwargs)
        self.w = width
        self.h = height
        self.pack_propagate(False)

        self.canvas = tk.Canvas(
            self,
            width=self.w,
            height=self.h,
            bg=Theme.BG_CARD,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

    def draw_chart(self, price_points: list[float]):
        """5 to 7 days ke closing prices se clean trend line draw karta hai"""
        self.canvas.delete("all")
        if not price_points or len(price_points) < 2:
            # Baseline placeholder
            self.canvas.create_line(4, self.h // 2, self.w - 4, self.h // 2, fill=Theme.BORDER_SUBTLE, width=1, dash=(2, 2))
            return

        min_p = min(price_points)
        max_p = max(price_points)
        diff = max_p - min_p if max_p != min_p else 1.0

        pad_x = 4
        pad_y = 5
        usable_w = self.w - (pad_x * 2)
        usable_h = self.h - (pad_y * 2)

        # Coordinates calculation
        step_x = usable_w / (len(price_points) - 1)
        coords = []
        for idx, p in enumerate(price_points):
            cx = pad_x + (idx * step_x)
            cy = pad_y + (usable_h - ((p - min_p) / diff * usable_h))
            coords.append((cx, cy))

        # Color: Start vs End
        is_bullish = price_points[-1] >= price_points[0]
        line_color = Theme.GREEN_BUY if is_bullish else Theme.RED_SELL

        # Draw smooth polyline
        flat_coords = [c for pt in coords for c in pt]
        self.canvas.create_line(flat_coords, fill=line_color, width=2, smooth=True, capstyle="round")

        # End-point glowing dot
        last_x, last_y = coords[-1]
        self.canvas.create_oval(last_x - 2, last_y - 2, last_x + 2, last_y + 2, fill=line_color, outline=line_color)

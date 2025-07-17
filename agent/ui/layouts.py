from rich.layout import Layout


def create_main_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=8),
    )
    layout["main"].split_row(
        Layout(name="plan_status", ratio=2), Layout(name="context", ratio=1)
    )
    return layout

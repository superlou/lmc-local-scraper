from nicegui import ui
import pandas as pd


def main():
    events = pd.read_csv("gen/events.csv")
    for i, event in events.iterrows():
        ui.link(f"{event.event} ({event.organization})", event.link)
        with ui.list():
            ui.item(event.when)
            ui.item(event.location)
            ui.item(event.description)


main()
ui.run()
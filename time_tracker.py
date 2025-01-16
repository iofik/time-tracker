#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import pandas as pd
from datetime import datetime, timedelta
import os

class TimeTrackerApp:
    def __init__(self):
        self.sessions = []
        self.current_session = None

        # Create an Application Indicator
        self.indicator = AppIndicator3.Indicator.new(
            "time-tracker",
            "gtk-media-record",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Create a menu
        self.menu = Gtk.Menu()

        # Start/Stop item
        self.start_stop_item = Gtk.MenuItem.new_with_label("Start")
        self.start_stop_item.connect("activate", self.on_start_stop_clicked)
        self.menu.append(self.start_stop_item)

        # Exit item
        exit_item = Gtk.MenuItem.new_with_label("Exit")
        exit_item.connect("activate", Gtk.main_quit)
        self.menu.append(exit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Load existing sessions
        self.load_sessions()

        # Update the tray icon every second
        GLib.timeout_add_seconds(1, self.update_tray_icon)

    def on_start_stop_clicked(self, item):
        if self.current_session:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.current_session = {
            'start': datetime.now(),
            'end': None,
            'project': 'Project',
            'task': 'Task'
        }
        self.start_stop_item.set_label("Stop")
        self.update_tray_icon()

    def stop_timer(self):
        if self.current_session:
            self.current_session['end'] = datetime.now()
            self.sessions.append(self.current_session)
            self.save_sessions()
            self.current_session = None
            self.start_stop_item.set_label("Start")
            self.update_tray_icon()

    def update_tray_icon(self):
        total_today = self.get_total_time_today()
        total_week = self.get_total_time_week()
        
        # Update the label in the tray
        self.indicator.set_label(f"Today: {total_today}", "")
        
        # Update the tooltip using the menu item
        self.start_stop_item.set_tooltip_text(f"Today: {total_today}\nWeek: {total_week}")
        
        return True  # Continue updating

    def get_total_time_today(self):
        today = datetime.now().date()
        total = timedelta()
        for session in self.sessions:
            if session['start'].date() == today:
                end = session['end'] if session['end'] else datetime.now()
                total += end - session['start']
        return str(total)

    def get_total_time_week(self):
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        total = timedelta()
        for session in self.sessions:
            if session['start'].date() >= start_of_week:
                end = session['end'] if session['end'] else datetime.now()
                total += end - session['start']
        return str(total)

    def save_sessions(self):
        now = datetime.now()
        filename = now.strftime("%Y-%m.csv")
        df = pd.DataFrame(self.sessions)
        if os.path.exists(filename):
            df.to_csv(filename, mode='a', header=False, index=False)
        else:
            df.to_csv(filename, index=False)

    def load_sessions(self):
        now = datetime.now()
        filename = now.strftime("%Y-%m.csv")
        if os.path.exists(filename):
            df = pd.read_csv(filename, parse_dates=['start', 'end'])
            self.sessions = df.to_dict('records')

if __name__ == "__main__":
    app = TimeTrackerApp()
    Gtk.main()

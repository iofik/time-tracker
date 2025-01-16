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
            "gtk-media-record",  # Иконка по умолчанию
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
            'start_ts': int(datetime.now().timestamp()),
            'end_ts': None,
            'project': 'Project',
            'task': 'Task'
        }
        self.start_stop_item.set_label("Stop")
        self.indicator.set_icon_full("gtk-media-record", "Timer Running")  # Зелёная иконка
        self.update_tray_icon()

    def stop_timer(self):
        if self.current_session:
            self.current_session['end_ts'] = int(datetime.now().timestamp())
            self.sessions.append(self.current_session)
            self.save_sessions()
            self.current_session = None
            self.start_stop_item.set_label("Start")
            self.indicator.set_icon_full("gtk-media-record", "Timer Stopped")  # Иконка по умолчанию
            self.update_tray_icon()

    def update_tray_icon(self):
        total_today = self.get_total_time_today()
        total_week = self.get_total_time_week()

        # Форматируем время до минут
        total_today_str = self.format_time(total_today)
        total_week_str = self.format_time(total_week)

        # Обновляем лейбл в трее
        self.indicator.set_label(f"Today: {total_today_str}", "")

        # Обновляем всплывающую подсказку
        self.start_stop_item.set_tooltip_text(f"Today: {total_today_str}\nWeek: {total_week_str}")

        return True  # Продолжаем обновление

    def format_time(self, td):
        """Форматирует timedelta в строку с точностью до минут."""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}"

    def get_total_time_today(self):
        today = datetime.now().date()
        total = timedelta()
        for session in self.sessions:
            if datetime.fromtimestamp(session['start_ts']).date() == today:
                end = datetime.fromtimestamp(session['end_ts']) if session['end_ts'] else datetime.now()
                start = datetime.fromtimestamp(session['start_ts'])
                total += end - start
        if self.current_session:
            # Добавляем текущую сессию, если таймер запущен
            end = datetime.now()
            start = datetime.fromtimestamp(self.current_session['start_ts'])
            total += end - start
        return total

    def get_total_time_week(self):
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        total = timedelta()
        for session in self.sessions:
            if datetime.fromtimestamp(session['start_ts']).date() >= start_of_week:
                end = datetime.fromtimestamp(session['end_ts']) if session['end_ts'] else datetime.now()
                start = datetime.fromtimestamp(session['start_ts'])
                total += end - start
        if self.current_session:
            # Добавляем текущую сессию, если таймер запущен
            end = datetime.now()
            start = datetime.fromtimestamp(self.current_session['start_ts'])
            total += end - start
        return total

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
            df = pd.read_csv(filename)
            self.sessions = df.to_dict('records')

if __name__ == "__main__":
    app = TimeTrackerApp()
    Gtk.main()

#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import pandas as pd
from datetime import datetime, timedelta
import os
import json

class TimeTrackerApp:
    def __init__(self):
        self.sessions = []
        self.current_session = None
        self.projects = {}  # Словарь проектов и задач
        self.cache_file = "task_cache.json"  # Файл для кэширования проектов и задач

        # Загружаем кэш проектов и задач
        self.load_cache()

        # Create an Application Indicator
        self.indicator = AppIndicator3.Indicator.new(
            "time-tracker",
            "gtk-media-record",  # Иконка по умолчанию (зелёная)
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Create a menu
        self.menu = Gtk.Menu()

        # Start/Stop item
        self.start_stop_item = Gtk.MenuItem.new_with_label("Start")
        self.start_stop_item.connect("activate", self.on_start_stop_clicked)
        self.menu.append(self.start_stop_item)

        # Task item
        task_item = Gtk.MenuItem.new_with_label("Task")
        task_item.connect("activate", self.on_task_clicked)
        self.menu.append(task_item)

        # Day statistics item
        self.day_item = Gtk.MenuItem.new_with_label("Day: 00:00")
        self.day_item.set_sensitive(False)  # Делаем пункт неактивным
        self.menu.append(self.day_item)

        # Week statistics item
        self.week_item = Gtk.MenuItem.new_with_label("Week: 00:00")
        self.week_item.set_sensitive(False)  # Делаем пункт неактивным
        self.menu.append(self.week_item)

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

    def on_task_clicked(self, item):
        # Показываем диалог выбора проекта и задачи
        dialog = TaskDialog(self.projects)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            project, task = dialog.get_selected_task()
            if project and task:
                # Если таймер запущен, останавливаем текущую сессию
                if self.current_session:
                    self.stop_timer()

                # Начинаем новую сессию с выбранными проектом и задачей
                self.start_timer(project, task)

        dialog.destroy()

    def get_last_task_name(self):
        """Возвращает название последнего выполненного таска."""
        if self.sessions:
            return self.sessions[-1]['task']
        return "No tasks"

    def start_timer(self, project="Project", task="Task"):
        self.current_session = {
            'start_ts': int(datetime.now().timestamp()),
            'end_ts': None,
            'project': project,
            'task': task
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
            self.indicator.set_icon_full("gtk-media-pause", "Timer Stopped")  # Серая иконка
            self.update_tray_icon()

    def update_tray_icon(self):
        if self.current_session:
            # Время текущей сессии
            start_time = datetime.fromtimestamp(self.current_session['start_ts'])
            current_time = datetime.now()
            session_duration = current_time - start_time
            session_duration_str = self.format_time(session_duration)

            # Надпись в трее: "HH:MM Task name"
            task_name = self.current_session['task']
            self.indicator.set_label(f"{session_duration_str} {task_name}", "")
        else:
            # Когда таймер остановлен, показываем общее время за день и последний таск
            total_day = self.get_total_time_day()
            total_day_str = self.format_time(total_day)
            last_task = self.get_last_task_name()
            self.indicator.set_label(f"{total_day_str} {last_task}", "")

        # Обновляем статистику в меню
        total_day = self.get_total_time_day()
        total_week = self.get_total_time_week()
        total_day_str = self.format_time(total_day)
        total_week_str = self.format_time(total_week)

        self.day_item.set_label(f"Day: {total_day_str}")
        self.week_item.set_label(f"Week: {total_week_str}")

        return True  # Продолжаем обновление

    def format_time(self, td):
        """Форматирует timedelta в строку с точностью до минут."""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}"

    def get_total_time_day(self):
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

    def load_cache(self):
        """Загружает кэш проектов и задач из файла."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                self.projects = json.load(f)

    def save_cache(self):
        """Сохраняет кэш проектов и задач в файл."""
        with open(self.cache_file, "w") as f:
            json.dump(self.projects, f)

class TaskDialog(Gtk.Dialog):
    def __init__(self, projects, parent=None):
        super().__init__(title="Select Task", parent=parent, flags=0)
        self.projects = projects
        self.selected_project = None
        self.selected_task = None

        self.set_default_size(300, 150)

        # Создаем контейнер для элементов
        self.box = self.get_content_area()

        # Project combo box
        self.project_combo = Gtk.ComboBoxText.new_with_entry()
        self.project_combo.set_entry_text_column(0)
        for project in self.projects.keys():
            self.project_combo.append_text(project)
        self.project_combo.append_text("New Project")
        self.project_combo.set_active(0)

        # Task combo box
        self.task_combo = Gtk.ComboBoxText.new_with_entry()
        self.task_combo.set_entry_text_column(0)
        self.task_combo.append_text("New Task")
        self.task_combo.set_active(0)

        # Подключаем сигнал изменения проекта после инициализации task_combo
        self.project_combo.connect("changed", self.on_project_changed)

        # Создаем сетку для размещения элементов
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.attach(Gtk.Label(label="Project:"), 0, 0, 1, 1)
        grid.attach(self.project_combo, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Task:"), 0, 1, 1, 1)
        grid.attach(self.task_combo, 1, 1, 1, 1)

        # Добавляем сетку в диалоговое окно
        self.box.add(grid)

        # Добавляем кнопки OK и Cancel
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)

        # Показываем все элементы
        self.show_all()

    def on_project_changed(self, combo):
        project = combo.get_active_text()
        if project == "New Project":
            self.task_combo.remove_all()
            self.task_combo.append_text("New Task")
            self.task_combo.set_active(0)
        else:
            self.task_combo.remove_all()
            for task in self.projects.get(project, []):
                self.task_combo.append_text(task)
            self.task_combo.append_text("New Task")
            self.task_combo.set_active(0)

    def get_selected_task(self):
        project = self.project_combo.get_active_text()
        task = self.task_combo.get_active_text()

        if project == "New Project":
            project = self.project_combo.get_child().get_text()
            if not project:
                return None, None

        if task == "New Task":
            task = self.task_combo.get_child().get_text()
            if not task:
                return None, None

        # Обновляем кэш проектов и задач
        if project not in self.projects:
            self.projects[project] = []
        if task not in self.projects[project]:
            self.projects[project].append(task)

        return project, task

if __name__ == "__main__":
    app = TimeTrackerApp()
    Gtk.main()

import flet as ft
import json
import os
import threading
import time
from datetime import datetime, timedelta
import sqlite3
import random

# ============= دیتابیس =============

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('advanced_tasks.db')
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # جدول کارها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                priority TEXT,
                eisenhower_type TEXT,
                done INTEGER DEFAULT 0,
                deadline TEXT,
                created TEXT,
                reminder TEXT,
                notes TEXT,
                estimated_time INTEGER DEFAULT 0,
                actual_time INTEGER DEFAULT 0,
                energy_level TEXT
            )
        ''')
        
        # جدول اهداف
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                goal_type TEXT,
                target_date TEXT,
                progress INTEGER DEFAULT 0,
                created TEXT
            )
        ''')
        
        # جدول عادت‌ها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                frequency TEXT,
                streak INTEGER DEFAULT 0,
                last_done TEXT,
                created TEXT
            )
        ''')
        
        # جدول پومودورو
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                sessions INTEGER DEFAULT 0,
                total_time INTEGER DEFAULT 0
            )
        ''')
        
        # جدول انرژی
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_energy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                energy_level TEXT,
                mood TEXT,
                notes TEXT
            )
        ''')
        
        # جدول گیمیفیکیشن
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gamification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                streak INTEGER DEFAULT 0,
                badges TEXT,
                total_focus_time INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
    
    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

# ============= کلاس‌های اصلی =============

class TaskManager:
    def __init__(self, db):
        self.db = db
        self.tasks = []
        self.load()
    
    def load(self):
        self.db.cursor.execute('SELECT * FROM tasks ORDER BY done, priority DESC')
        rows = self.db.cursor.fetchall()
        self.tasks = []
        for row in rows:
            self.tasks.append({
                'id': row[0],
                'title': row[1],
                'category': row[2],
                'priority': row[3],
                'eisenhower_type': row[4],
                'done': bool(row[5]),
                'deadline': row[6],
                'created': row[7],
                'reminder': row[8],
                'notes': row[9],
                'estimated_time': row[10],
                'actual_time': row[11],
                'energy_level': row[12]
            })
    
    def add(self, title, category="سایر", priority="متوسط", eisenhower_type="مهم و غیر فوری", 
            deadline=None, reminder=None, notes="", estimated_time=0, energy_level="متوسط"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.execute(
            '''INSERT INTO tasks 
            (title, category, priority, eisenhower_type, deadline, created, reminder, notes, estimated_time, energy_level) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, category, priority, eisenhower_type, deadline, now, reminder, notes, estimated_time, energy_level)
        )
        self.load()
        return self.tasks[-1] if self.tasks else None
    
    def delete(self, task_id):
        self.db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.load()
    
    def toggle(self, task_id):
        self.db.cursor.execute('SELECT done FROM tasks WHERE id = ?', (task_id,))
        done = self.db.cursor.fetchone()
        if done:
            new_done = 0 if done[0] else 1
            self.db.execute('UPDATE tasks SET done = ? WHERE id = ?', (new_done, task_id))
            self.load()
            return bool(new_done)
        return False
    
    def get_stats(self):
        total = len(self.tasks)
        done = len([t for t in self.tasks if t['done']])
        categories = {}
        priorities = {}
        eisenhower = {}
        for task in self.tasks:
            cat = task.get('category', 'سایر')
            categories[cat] = categories.get(cat, 0) + 1
            pri = task.get('priority', 'متوسط')
            priorities[pri] = priorities.get(pri, 0) + 1
            eis = task.get('eisenhower_type', 'مهم و غیر فوری')
            eisenhower[eis] = eisenhower.get(eis, 0) + 1
        return {
            'total': total,
            'done': done,
            'pending': total - done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'categories': categories,
            'priorities': priorities,
            'eisenhower': eisenhower
        }
    
    def get_tasks_by_eisenhower(self, eisenhower_type):
        return [t for t in self.tasks if t.get('eisenhower_type') == eisenhower_type and not t['done']]
    
    def get_today_tasks(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return [t for t in self.tasks if t.get('created', '').startswith(today) and not t['done']]

class Gamification:
    def __init__(self, db):
        self.db = db
        self.points = 0
        self.level = 1
        self.streak = 0
        self.badges = []
        self.total_focus_time = 0
        self.load()
    
    def load(self):
        self.db.cursor.execute('SELECT points, level, streak, badges, total_focus_time FROM gamification ORDER BY id DESC LIMIT 1')
        row = self.db.cursor.fetchone()
        if row:
            self.points = row[0]
            self.level = row[1]
            self.streak = row[2]
            self.badges = json.loads(row[3]) if row[3] else []
            self.total_focus_time = row[4]
        else:
            self.db.execute(
                'INSERT INTO gamification (points, level, streak, badges, total_focus_time) VALUES (0, 1, 0, "[]", 0)'
            )
    
    def save(self):
        self.db.execute(
            'UPDATE gamification SET points = ?, level = ?, streak = ?, badges = ?, total_focus_time = ? WHERE id = 1',
            (self.points, self.level, self.streak, json.dumps(self.badges), self.total_focus_time)
        )
    
    def add_points(self, points):
        self.points += points
        self.streak += 1
        self.check_level_up()
        self.save()
        return self.get_status()
    
    def add_focus_time(self, minutes):
        self.total_focus_time += minutes
        self.save()
    
    def check_level_up(self):
        new_level = self.points // 100 + 1
        if new_level > self.level:
            self.level = new_level
            self.add_badge(f"سطح {self.level}")
            return True
        return False
    
    def add_badge(self, badge):
        if badge not in self.badges:
            self.badges.append(badge)
            self.save()
    
    def get_status(self):
        return {
            'points': self.points,
            'level': self.level,
            'streak': self.streak,
            'badges': self.badges,
            'total_focus_time': self.total_focus_time
        }

class HabitManager:
    def __init__(self, db):
        self.db = db
        self.habits = []
        self.load()
    
    def load(self):
        self.db.cursor.execute('SELECT * FROM habits')
        rows = self.db.cursor.fetchall()
        self.habits = []
        for row in rows:
            self.habits.append({
                'id': row[0],
                'name': row[1],
                'frequency': row[2],
                'streak': row[3],
                'last_done': row[4],
                'created': row[5]
            })
    
    def add(self, name, frequency="روزانه"):
        now = datetime.now().strftime("%Y-%m-%d")
        self.db.execute(
            'INSERT INTO habits (name, frequency, created) VALUES (?, ?, ?)',
            (name, frequency, now)
        )
        self.load()
        return self.habits[-1] if self.habits else None
    
    def mark_done(self, habit_id):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.cursor.execute('SELECT last_done, streak FROM habits WHERE id = ?', (habit_id,))
        row = self.db.cursor.fetchone()
        if row:
            last_done = row[0]
            streak = row[1]
            if last_done != today:
                if last_done and (datetime.now() - datetime.strptime(last_done, "%Y-%m-%d")).days == 1:
                    streak += 1
                else:
                    streak = 1
                self.db.execute(
                    'UPDATE habits SET last_done = ?, streak = ? WHERE id = ?',
                    (today, streak, habit_id)
                )
        self.load()

class SimpleAI:
    @staticmethod
    def suggest_daily_plan(tasks, energy_level="متوسط"):
        if not tasks:
            return "امروز هیچ کاری ندارید! استراحت کنید."
        
        high_priority = [t for t in tasks if t.get('priority') == "بالا"]
        
        if energy_level == "زیاد":
            suggestion = "✨ انرژی بالا! زمان کارهای سخت:\n"
            if high_priority:
                suggestion += "🔴 کارهای مهم امروز:\n"
                for t in high_priority[:3]:
                    suggestion += f"  • {t['title']}\n"
            return suggestion
        elif energy_level == "کم":
            return "😴 انرژی کم است. کارهای سبک انجام دهید."
        else:
            suggestion = "⚡ انرژی متوسط. تعادل را رعایت کنید.\n"
            if high_priority:
                suggestion += f"🎯 کارهای مهم:\n"
                for t in high_priority[:2]:
                    suggestion += f"  • {t['title']}\n"
            return suggestion

# ============= صفحه‌های برنامه =============

class DashboardPage:
    def __init__(self, page, task_manager, gamification):
        self.page = page
        self.task_manager = task_manager
        self.gamification = gamification
        self.build()
    
    def build(self):
        stats = self.task_manager.get_stats()
        g_status = self.gamification.get_status()
        
        cards = ft.Row([
            ft.Card(ft.Container(ft.Column([
                ft.Text(f"📋 {stats['total']}", size=24),
                ft.Text("مجموع", size=12)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10, width=80)),
            ft.Card(ft.Container(ft.Column([
                ft.Text(f"✅ {stats['done']}", size=24, color=ft.Colors.GREEN_700),
                ft.Text("انجام شده", size=12)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10, width=80)),
            ft.Card(ft.Container(ft.Column([
                ft.Text(f"⏳ {stats['pending']}", size=24, color=ft.Colors.RED_700),
                ft.Text("باقی مانده", size=12)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10, width=80)),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        progress = ft.Column([
            ft.Text(f"📈 پیشرفت: {stats['completion_rate']:.1f}%"),
            ft.ProgressBar(value=stats['completion_rate']/100, height=10, color=ft.Colors.BLUE_700)
        ], spacing=5)
        
        gamification_card = ft.Card(
            ft.Container(
                ft.Column([
                    ft.Text(f"⭐ {g_status['points']} امتیاز", size=18),
                    ft.Text(f"🏅 سطح {g_status['level']}"),
                    ft.Text(f"🔥 {g_status['streak']} روز"),
                    ft.Row([ft.Text(badge, size=12) for badge in g_status['badges']])
                ]),
                padding=15
            )
        )
        
        ai_suggestion = ft.Card(
            ft.Container(
                ft.Column([
                    ft.Text("🤖 پیشنهاد AI", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(SimpleAI.suggest_daily_plan(
                        self.task_manager.get_today_tasks(), 
                        "متوسط"
                    ), size=14)
                ]),
                padding=15
            )
        )
        
        self.page.add(
            ft.Text("📊 داشبورد", size=24, weight=ft.FontWeight.BOLD),
            cards,
            progress,
            gamification_card,
            ai_suggestion
        )

class TaskPage:
    def __init__(self, page, task_manager, gamification, db):
        self.page = page
        self.task_manager = task_manager
        self.gamification = gamification
        self.db = db
        self.task_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.build()
    
    def build(self):
        add_button = ft.FloatingActionButton(
            icon="ADD",
            bgcolor=ft.Colors.BLUE_700,
            on_click=lambda _: self.show_add_task_dialog()
        )
        
        self.page.add(
            ft.Text("📋 کارها", size=24, weight=ft.FontWeight.BOLD),
            self.task_list,
            add_button
        )
        self.update_task_list()
    
    def show_add_task_dialog(self):
        title_input = ft.TextField(hint_text="عنوان کار", rtl=True)
        category_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("کار", "کار"),
                ft.dropdown.Option("شخصی", "شخصی"),
                ft.dropdown.Option("مطالعه", "مطالعه"),
                ft.dropdown.Option("سلامت", "سلامت"),
            ],
            value="کار",
            rtl=True
        )
        priority_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("بالا", "بالا"),
                ft.dropdown.Option("متوسط", "متوسط"),
                ft.dropdown.Option("پایین", "پایین"),
            ],
            value="متوسط",
            rtl=True
        )
        eisenhower_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("مهم و فوری", "مهم و فوری"),
                ft.dropdown.Option("مهم و غیر فوری", "مهم و غیر فوری"),
                ft.dropdown.Option("غیر مهم و فوری", "غیر مهم و فوری"),
                ft.dropdown.Option("حذف‌شدنی", "حذف‌شدنی"),
            ],
            value="مهم و غیر فوری",
            rtl=True
        )
        deadline_input = ft.TextField(hint_text="تاریخ سررسید (اختیاری)", rtl=True)
        notes_input = ft.TextField(hint_text="یادداشت (اختیاری)", multiline=True, rtl=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("کار جدید", rtl=True),
            content=ft.Column([
                title_input,
                ft.Row([category_dropdown, priority_dropdown]),
                eisenhower_dropdown,
                deadline_input,
                notes_input,
            ], tight=True),
            actions=[
                ft.TextButton("لغو", on_click=lambda _: self.close_dialog()),
                ft.TextButton("افزودن", on_click=lambda _: self.add_task(
                    title_input.value,
                    category_dropdown.value,
                    priority_dropdown.value,
                    eisenhower_dropdown.value,
                    deadline_input.value,
                    notes_input.value
                )),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def add_task(self, title, category, priority, eisenhower, deadline, notes):
        if title and title.strip():
            task = self.task_manager.add(
                title.strip(), category, priority, eisenhower, deadline, None, notes
            )
            self.gamification.add_points(5)
            self.close_dialog()
            self.update_task_list()
            self.page.snack_bar = ft.SnackBar(ft.Text("✅ کار اضافه شد! +۵ امتیاز"))
            self.page.snack_bar.open = True
            self.page.update()
    
    def close_dialog(self):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def update_task_list(self):
        self.task_list.controls.clear()
        
        priority_colors = {
            "بالا": ft.Colors.RED_700,
            "متوسط": ft.Colors.ORANGE_700,
            "پایین": ft.Colors.GREEN_700
        }
        
        for task in self.task_manager.tasks:
            if task['done']:
                continue
            
            task_card = ft.Card(
                ft.Container(
                    ft.Row([
                        ft.Checkbox(
                            value=task['done'],
                            on_change=lambda e, t=task: self.toggle_task(t['id'])
                        ),
                        ft.Column([
                            ft.Text(task['title'], size=16, rtl=True),
                            ft.Row([
                                ft.Text(task.get('category', ''), size=12),
                                ft.Container(
                                    ft.Text(task.get('priority', ''), size=10, color=ft.Colors.WHITE),
                                    bgcolor=priority_colors.get(task.get('priority', 'متوسط'), ft.Colors.GREY),
                                    padding=5,
                                    border_radius=5
                                ),
                                ft.Text(task.get('eisenhower_type', ''), size=10)
                            ])
                        ], expand=True),
                        ft.IconButton(
                            icon="DELETE",
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda e, t=task: self.delete_task(t['id'])
                        )
                    ]),
                    padding=10
                )
            )
            self.task_list.controls.append(task_card)
        
        if not self.task_list.controls:
            self.task_list.controls.append(
                ft.Text("🎯 همه کارها انجام شد!", size=16, color=ft.Colors.GREY_500)
            )
        
        self.page.update()
    
    def toggle_task(self, task_id):
        done = self.task_manager.toggle(task_id)
        if done:
            self.gamification.add_points(10)
            self.page.snack_bar = ft.SnackBar(ft.Text("🎉 +۱۰ امتیاز!"))
            self.page.snack_bar.open = True
        self.update_task_list()
        self.page.update()
    
    def delete_task(self, task_id):
        self.task_manager.delete(task_id)
        self.update_task_list()
        self.page.update()

class EisenhowerMatrixPage:
    def __init__(self, page, task_manager):
        self.page = page
        self.task_manager = task_manager
        self.build()
    
    def build(self):
        types = [
            ("🔴 مهم و فوری", "مهم و فوری"),
            ("🟡 مهم و غیر فوری", "مهم و غیر فوری"),
            ("🟠 غیر مهم و فوری", "غیر مهم و فوری"),
            ("⚪ حذف‌شدنی", "حذف‌شدنی")
        ]
        
        matrix = ft.Column()
        row1 = ft.Row()
        row2 = ft.Row()
        
        for i, (label, eisenhower_type) in enumerate(types):
            tasks = self.task_manager.get_tasks_by_eisenhower(eisenhower_type)
            card = self.create_matrix_card(label, eisenhower_type, tasks)
            if i < 2:
                row1.controls.append(card)
            else:
                row2.controls.append(card)
        
        matrix.controls.append(row1)
        matrix.controls.append(row2)
        
        self.page.add(
            ft.Text("📊 ماتریس آیزنهاور", size=24, weight=ft.FontWeight.BOLD),
            matrix
        )
    
    def create_matrix_card(self, title, eisenhower_type, tasks):
        return ft.Card(
            ft.Container(
                ft.Column([
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"تعداد: {len(tasks)}", size=12),
                    ft.Column([
                        ft.Text(f"• {t['title']}", size=12, rtl=True) for t in tasks[:3]
                    ]) if tasks else ft.Text("✅ خالی!", size=12, color=ft.Colors.GREY_500)
                ]),
                padding=10,
                width=180,
                height=150,
                bgcolor=self.get_color(eisenhower_type)
            )
        )
    
    def get_color(self, eisenhower_type):
        colors = {
            "مهم و فوری": ft.Colors.RED_100,
            "مهم و غیر فوری": ft.Colors.YELLOW_100,
            "غیر مهم و فوری": ft.Colors.ORANGE_100,
            "حذف‌شدنی": ft.Colors.GREY_200
        }
        return colors.get(eisenhower_type, ft.Colors.WHITE)

class PomodoroPage:
    def __init__(self, page, db, gamification):
        self.page = page
        self.db = db
        self.gamification = gamification
        self.work_time = 25 * 60
        self.break_time = 5 * 60
        self.is_running = False
        self.is_work = True
        self.remaining = self.work_time
        self.sessions = 0
        self.thread = None
        self.build()
    
    def build(self):
        self.display = ft.Text("25:00", size=48, weight=ft.FontWeight.BOLD)
        
        controls = ft.Row([
            ft.IconButton(
                icon="PLAY_CIRCLE",
                icon_size=40,
                on_click=self.start,
                icon_color=ft.Colors.GREEN_700
            ),
            ft.IconButton(
                icon="STOP_CIRCLE",
                icon_size=40,
                on_click=self.stop,
                icon_color=ft.Colors.RED_700
            ),
            ft.IconButton(
                icon="REFRESH",
                icon_size=40,
                on_click=self.reset,
                icon_color=ft.Colors.ORANGE_700
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        info = ft.Text("⏱️ ۲۵ دقیقه کار | ۵ دقیقه استراحت", size=14)
        stats = ft.Text(f"📊 جلسات امروز: {self.get_today_sessions()}", size=14)
        
        self.page.add(
            ft.Text("🍅 پومودورو", size=24, weight=ft.FontWeight.BOLD),
            self.display,
            controls,
            info,
            stats
        )
    
    def start(self, e):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
    
    def stop(self, e):
        self.is_running = False
    
    def reset(self, e):
        self.stop()
        self.is_work = True
        self.remaining = self.work_time
        self.update_display()
    
    def _run(self):
        while self.is_running and self.remaining > 0:
            time.sleep(1)
            self.remaining -= 1
            self.update_display()
        
        if self.remaining == 0 and self.is_running:
            self.sessions += 1
            self.save_session()
            self.gamification.add_points(10)
            self.switch_mode()
    
    def switch_mode(self):
        self.is_work = not self.is_work
        self.remaining = self.work_time if self.is_work else self.break_time
        message = "🔴 زمان تمرکز!" if self.is_work else "🟢 زمان استراحت!"
        self.page.snack_bar = ft.SnackBar(ft.Text(message), duration=3000)
        self.page.snack_bar.open = True
        self.page.update()
        self.start(None)
    
    def update_display(self):
        minutes = self.remaining // 60
        seconds = self.remaining % 60
        self.display.value = f"{minutes:02d}:{seconds:02d}"
        self.display.update()
    
    def save_session(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.cursor.execute(
            'SELECT sessions FROM pomodoro_sessions WHERE date = ?',
            (today,)
        )
        row = self.db.cursor.fetchone()
        if row:
            self.db.execute(
                'UPDATE pomodoro_sessions SET sessions = ? WHERE date = ?',
                (row[0] + 1, today)
            )
        else:
            self.db.execute(
                'INSERT INTO pomodoro_sessions (date, sessions) VALUES (?, ?)',
                (today, 1)
            )
    
    def get_today_sessions(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.cursor.execute(
            'SELECT sessions FROM pomodoro_sessions WHERE date = ?',
            (today,)
        )
        row = self.db.cursor.fetchone()
        return row[0] if row else 0

class HabitTrackerPage:
    def __init__(self, page, habit_manager, gamification):
        self.page = page
        self.habit_manager = habit_manager
        self.gamification = gamification
        self.build()
    
    def build(self):
        habits_list = ft.Column()
        
        for habit in self.habit_manager.habits:
            habit_row = ft.Row([
                ft.Text(f"• {habit['name']}", size=16, rtl=True),
                ft.Text(f"🔥 {habit['streak']} روز", size=12, color=ft.Colors.ORANGE_700),
                ft.IconButton(
                    icon="CHECK_CIRCLE",
                    icon_color=ft.Colors.GREEN_700,
                    on_click=lambda e, h=habit: self.mark_habit_done(h['id'])
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            habits_list.controls.append(habit_row)
        
        add_button = ft.ElevatedButton(
            "➕ عادت جدید",
            on_click=lambda _: self.show_add_habit_dialog()
        )
        
        self.page.add(
            ft.Text("🔄 مدیریت عادت‌ها", size=24, weight=ft.FontWeight.BOLD),
            habits_list,
            add_button
        )
    
    def mark_habit_done(self, habit_id):
        self.habit_manager.mark_done(habit_id)
        self.gamification.add_points(5)
        self.page.snack_bar = ft.SnackBar(ft.Text("✅ عادت ثبت شد! +۵ امتیاز"))
        self.page.snack_bar.open = True
        self.page.update()
    
    def show_add_habit_dialog(self):
        name_input = ft.TextField(hint_text="نام عادت", rtl=True)
        frequency_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("روزانه", "روزانه"),
                ft.dropdown.Option("هفتگی", "هفتگی"),
            ],
            value="روزانه",
            rtl=True
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text("عادت جدید", rtl=True),
            content=ft.Column([name_input, frequency_dropdown]),
            actions=[
                ft.TextButton("لغو", on_click=lambda _: self.close_dialog()),
                ft.TextButton("افزودن", on_click=lambda _: self.add_habit(name_input.value, frequency_dropdown.value)),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def add_habit(self, name, frequency):
        if name and name.strip():
            self.habit_manager.add(name.strip(), frequency)
            self.close_dialog()
            self.gamification.add_points(10)
            self.page.snack_bar = ft.SnackBar(ft.Text("✅ عادت جدید اضافه شد! +۱۰ امتیاز"))
            self.page.snack_bar.open = True
            self.page.update()
            self.build()
    
    def close_dialog(self):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

class FocusModePage:
    def __init__(self, page, db, gamification):
        self.page = page
        self.db = db
        self.gamification = gamification
        self.is_focus = False
        self.focus_time = 0
        self.timer = None
        self.build()
    
    def build(self):
        self.display = ft.Text("00:00:00", size=48, weight=ft.FontWeight.BOLD)
        
        controls = ft.Row([
            ft.IconButton(
                icon="PLAY_CIRCLE",
                icon_size=40,
                on_click=self.start_focus,
                icon_color=ft.Colors.GREEN_700
            ),
            ft.IconButton(
                icon="STOP_CIRCLE",
                icon_size=40,
                on_click=self.stop_focus,
                icon_color=ft.Colors.RED_700
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        info = ft.Text("⏱️ زمان تمرکز ثبت می‌شود", size=14, color=ft.Colors.GREY_600)
        
        self.page.add(
            ft.Text("🎯 حالت تمرکز", size=24, weight=ft.FontWeight.BOLD),
            self.display,
            controls,
            info,
            ft.Text(f"📊 زمان کل تمرکز: {self.gamification.total_focus_time} دقیقه", size=14)
        )
    
    def start_focus(self, e):
        if not self.is_focus:
            self.is_focus = True
            self.focus_time = 0
            self.timer = threading.Thread(target=self._run_focus, daemon=True)
            self.timer.start()
            self.page.snack_bar = ft.SnackBar(ft.Text("🔴 حالت تمرکز فعال شد!"))
            self.page.snack_bar.open = True
            self.page.update()
    
    def stop_focus(self, e):
        if self.is_focus:
            self.is_focus = False
            minutes = self.focus_time // 60
            self.gamification.add_focus_time(minutes)
            self.gamification.add_points(minutes // 5)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ {minutes} دقیقه تمرکز! +{minutes//5} امتیاز"))
            self.page.snack_bar.open = True
            self.page.update()
    
    def _run_focus(self):
        while self.is_focus:
            time.sleep(1)
            self.focus_time += 1
            minutes = self.focus_time // 60
            seconds = self.focus_time % 60
            self.display.value = f"{minutes:02d}:{seconds:02d}"
            self.display.update()

class DailyEnergyPage:
    def __init__(self, page, db):
        self.page = page
        self.db = db
        self.build()
    
    def build(self):
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.db.cursor.execute('SELECT energy_level FROM daily_energy WHERE date = ?', (today,))
        row = self.db.cursor.fetchone()
        current_energy = row[0] if row else "ثبت نشده"
        
        self.page.add(
            ft.Text("⚡ ثبت انرژی روزانه", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(f"📅 امروز: {today}", size=16),
            ft.Text(f"🔋 انرژی فعلی: {current_energy}", size=16),
            ft.Row([
                ft.ElevatedButton("⚡ زیاد", on_click=lambda _: self.set_energy("زیاد")),
                ft.ElevatedButton("⚡ متوسط", on_click=lambda _: self.set_energy("متوسط")),
                ft.ElevatedButton("⚡ کم", on_click=lambda _: self.set_energy("کم")),
            ])
        )
    
    def set_energy(self, level):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.execute(
            'INSERT OR REPLACE INTO daily_energy (date, energy_level) VALUES (?, ?)',
            (today, level)
        )
        self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ انرژی امروز: {level} ثبت شد!"))
        self.page.snack_bar.open = True
        self.page.update()
        self.build()

class ReportPage:
    def __init__(self, page, task_manager, gamification):
        self.page = page
        self.task_manager = task_manager
        self.gamification = gamification
        self.build()
    
    def build(self):
        stats = self.task_manager.get_stats()
        g_status = self.gamification.get_status()
        
        self.page.add(
            ft.Text("📊 گزارش عملکرد", size=24, weight=ft.FontWeight.BOLD),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("📋 آمار کلی", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"تعداد کل کارها: {stats['total']}"),
                        ft.Text(f"انجام شده: {stats['done']}"),
                        ft.Text(f"باقی مانده: {stats['pending']}"),
                        ft.Text(f"نرخ موفقیت: {stats['completion_rate']:.1f}%"),
                        ft.Text(f"دسته‌بندی‌ها: {', '.join(stats['categories'].keys())}"),
                        ft.Text(f"اولویت‌ها: {', '.join(stats['priorities'].keys())}"),
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("🏆 آمار گیمیفیکیشن", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"امتیاز: {g_status['points']}"),
                        ft.Text(f"سطح: {g_status['level']}"),
                        ft.Text(f"رکورد: {g_status['streak']} روز"),
                        ft.Text(f"زمان تمرکز: {g_status['total_focus_time']} دقیقه"),
                        ft.Text(f"نشان‌ها: {', '.join(g_status['badges']) if g_status['badges'] else 'هیچ'}")
                    ]),
                    padding=15
                )
            )
        )

class SettingsPage:
    def __init__(self, page, db, gamification):
        self.page = page
        self.db = db
        self.gamification = gamification
        self.build()
    
    def build(self):
        theme_toggle = ft.Switch(
            value=self.page.theme_mode == ft.ThemeMode.DARK,
            on_change=self.toggle_theme,
            label="🌙 حالت شب"
        )
        
        backup_button = ft.ElevatedButton(
            "💾 پشتیبان‌گیری",
            on_click=self.backup_data
        )
        
        reset_button = ft.ElevatedButton(
            "🔄 ریست کردن",
            on_click=self.reset_data,
            color=ft.Colors.RED_700
        )
        
        self.page.add(
            ft.Text("⚙️ تنظیمات", size=24, weight=ft.FontWeight.BOLD),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("ظاهر", size=18, weight=ft.FontWeight.BOLD),
                        theme_toggle,
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("داده‌ها", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([backup_button, reset_button]),
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("ℹ️ درباره برنامه", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("مدیریت زمان حرفه‌ای v2.0"),
                        ft.Text("طراحی شده برای بهبود بهره‌وری"),
                    ]),
                    padding=15
                )
            )
        )
    
    def toggle_theme(self, e):
        if e.control.value:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = ft.Colors.GREY_900
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = ft.Colors.WHITE
        self.page.update()
    
    def backup_data(self):
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy('advanced_tasks.db', f'backup_{timestamp}.db')
        self.page.snack_bar = ft.SnackBar(ft.Text("✅ پشتیبان‌گیری شد!"))
        self.page.snack_bar.open = True
        self.page.update()
    
    def reset_data(self):
        def confirm_reset():
            import os
            if os.path.exists('advanced_tasks.db'):
                os.remove('advanced_tasks.db')
            self.page.dialog.open = False
            self.page.snack_bar = ft.SnackBar(ft.Text("🔄 داده‌ها ریست شدند!"))
            self.page.snack_bar.open = True
            self.page.update()
            # ریستارت برنامه
            self.page.clean()
            self.build()
        
        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ تأیید ریست"),
            content=ft.Text("آیا از حذف همه داده‌ها مطمئن هستید؟"),
            actions=[
                ft.TextButton("لغو", on_click=lambda _: self.close_dialog()),
                ft.TextButton("ریست", on_click=lambda _: confirm_reset(), style=ft.ButtonStyle(color=ft.Colors.RED_700)),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_dialog(self):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

# ============= صفحه اصلی =============

async def main(page: ft.Page):
    page.title = "مدیریت زمان حرفه‌ای"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 10
    page.rtl = True
    page.bgcolor = ft.Colors.GREY_50
    
    db = Database()
    task_manager = TaskManager(db)
    gamification = Gamification(db)
    habit_manager = HabitManager(db)
    
    pages = {
        "داشبورد": DashboardPage(page, task_manager, gamification),
        "کارها": TaskPage(page, task_manager, gamification, db),
        "آیزنهاور": EisenhowerMatrixPage(page, task_manager),
        "پومودورو": PomodoroPage(page, db, gamification),
        "عادت‌ها": HabitTrackerPage(page, habit_manager, gamification),
        "تمرکز": FocusModePage(page, db, gamification),
        "انرژی": DailyEnergyPage(page, db),
        "گزارش": ReportPage(page, task_manager, gamification),
        "تنظیمات": SettingsPage(page, db, gamification)
    }
    
    destinations = [
        ft.NavigationDestination(icon="DASHBOARD", label="داشبورد"),
        ft.NavigationDestination(icon="LIST_ALT", label="کارها"),
        ft.NavigationDestination(icon="GRID_VIEW", label="آیزنهاور"),
        ft.NavigationDestination(icon="TIMER", label="پومودورو"),
        ft.NavigationDestination(icon="REPEAT", label="عادت‌ها"),
        ft.NavigationDestination(icon="FOCUS_MODE", label="تمرکز"),
        ft.NavigationDestination(icon="ENERGY_SAVINGS_LEAF", label="انرژی"),
        ft.NavigationDestination(icon="BAR_CHART", label="گزارش"),
        ft.NavigationDestination(icon="SETTINGS", label="تنظیمات"),
    ]
    
    page_list = ["داشبورد", "کارها", "آیزنهاور", "پومودورو", "عادت‌ها", "تمرکز", "انرژی", "گزارش", "تنظیمات"]
    
    def change_page(e):
        page.controls.clear()
        page.add(nav_bar)
        label = page_list[e.control.selected_index]
        page.add(pages[label])
        page.update()
    
    nav_bar = ft.NavigationBar(
        destinations=destinations,
        selected_index=0,
        on_change=change_page,
        bgcolor=ft.Colors.WHITE,
        elevation=5
    )
    
    page.add(nav_bar)
    page.add(pages["داشبورد"])
    page.update()

ft.app(target=main, assets_dir="assets")

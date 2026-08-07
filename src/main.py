import flet as ft
import json
import os
import threading
import time
from datetime import datetime, timedelta
import calendar
import sqlite3

# ============= دیتابیس SQLite =============

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('tasks.db')
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                priority TEXT,
                done INTEGER DEFAULT 0,
                deadline TEXT,
                created TEXT,
                reminder TEXT,
                notes TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                sessions INTEGER DEFAULT 0,
                total_time INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gamification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                streak INTEGER DEFAULT 0,
                badges TEXT
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
                'done': bool(row[4]),
                'deadline': row[5],
                'created': row[6],
                'reminder': row[7],
                'notes': row[8]
            })
    
    def add(self, title, category="سایر", priority="متوسط", deadline=None, reminder=None, notes=""):
        now = datetime.now().strftime("%Y-%m-%d")
        self.db.execute(
            'INSERT INTO tasks (title, category, priority, deadline, created, reminder, notes) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (title, category, priority, deadline, now, reminder, notes)
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
    
    def update(self, task_id, **kwargs):
        for key, value in kwargs.items():
            self.db.execute(f'UPDATE tasks SET {key} = ? WHERE id = ?', (value, task_id))
        self.load()
    
    def get_stats(self):
        total = len(self.tasks)
        done = len([t for t in self.tasks if t['done']])
        categories = {}
        priorities = {}
        for task in self.tasks:
            cat = task.get('category', 'سایر')
            categories[cat] = categories.get(cat, 0) + 1
            pri = task.get('priority', 'متوسط')
            priorities[pri] = priorities.get(pri, 0) + 1
        return {
            'total': total,
            'done': done,
            'pending': total - done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'categories': categories,
            'priorities': priorities
        }
    
    def get_today_tasks(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return [t for t in self.tasks if t.get('created') == today and not t['done']]
    
    def get_upcoming_deadlines(self):
        today = datetime.now().date()
        upcoming = []
        for task in self.tasks:
            if task.get('deadline') and not task['done']:
                try:
                    deadline_date = datetime.strptime(task['deadline'], "%Y-%m-%d").date()
                    if 0 <= (deadline_date - today).days <= 7:
                        upcoming.append(task)
                except:
                    pass
        return upcoming

class PomodoroTimer:
    def __init__(self, page, db):
        self.page = page
        self.db = db
        self.work_time = 25 * 60
        self.break_time = 5 * 60
        self.long_break_time = 15 * 60
        self.is_running = False
        self.is_work = True
        self.remaining = self.work_time
        self.sessions = 0
        self.thread = None
        self.callback = None
        
    def start(self, callback=None):
        if not self.is_running:
            self.is_running = True
            self.callback = callback
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
    
    def stop(self):
        self.is_running = False
    
    def reset(self):
        self.stop()
        self.is_work = True
        self.remaining = self.work_time
        self.sessions = 0
    
    def _run(self):
        while self.is_running and self.remaining > 0:
            time.sleep(1)
            self.remaining -= 1
            if self.callback:
                self.callback()
        
        if self.remaining == 0 and self.is_running:
            self.sessions += 1
            self.save_session()
            self.switch_mode()
    
    def switch_mode(self):
        self.is_work = not self.is_work
        if self.is_work:
            self.remaining = self.work_time
            message = "⏰ زمان تمرکز!"
            icon = "🔴"
        else:
            if self.sessions % 4 == 0:
                self.remaining = self.long_break_time
                message = "☕ استراحت طولانی!"
            else:
                self.remaining = self.break_time
                message = "☕ زمان استراحت!"
            icon = "🟢"
        
        self.page.snack_bar = ft.SnackBar(
            ft.Text(f"{icon} {message}"),
            duration=4000,
            bgcolor=ft.Colors.BLUE_700 if self.is_work else ft.Colors.GREEN_700
        )
        self.page.snack_bar.open = True
        self.page.update()
        self.start()
    
    def save_session(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.cursor.execute(
            'SELECT sessions, total_time FROM pomodoro_sessions WHERE date = ?',
            (today,)
        )
        row = self.db.cursor.fetchone()
        if row:
            self.db.execute(
                'UPDATE pomodoro_sessions SET sessions = ?, total_time = ? WHERE date = ?',
                (row[0] + 1, row[1] + self.work_time, today)
            )
        else:
            self.db.execute(
                'INSERT INTO pomodoro_sessions (date, sessions, total_time) VALUES (?, ?, ?)',
                (today, 1, self.work_time)
            )
    
    def get_time_string(self):
        minutes = self.remaining // 60
        seconds = self.remaining % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_today_sessions(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.db.cursor.execute(
            'SELECT sessions, total_time FROM pomodoro_sessions WHERE date = ?',
            (today,)
        )
        row = self.db.cursor.fetchone()
        return row if row else (0, 0)

class Gamification:
    def __init__(self, db):
        self.db = db
        self.points = 0
        self.level = 1
        self.streak = 0
        self.badges = []
        self.load()
    
    def load(self):
        self.db.cursor.execute('SELECT points, level, streak, badges FROM gamification ORDER BY id DESC LIMIT 1')
        row = self.db.cursor.fetchone()
        if row:
            self.points = row[0]
            self.level = row[1]
            self.streak = row[2]
            self.badges = json.loads(row[3]) if row[3] else []
        else:
            self.db.execute(
                'INSERT INTO gamification (points, level, streak, badges) VALUES (0, 1, 0, "[]")'
            )
    
    def save(self):
        self.db.execute(
            'UPDATE gamification SET points = ?, level = ?, streak = ?, badges = ? WHERE id = 1',
            (self.points, self.level, self.streak, json.dumps(self.badges))
        )
    
    def add_points(self, points, task=None):
        self.points += points
        self.streak += 1
        self.check_level_up()
        self.check_badges(task)
        self.save()
        return self.get_status()
    
    def check_level_up(self):
        new_level = self.points // 100 + 1
        if new_level > self.level:
            self.level = new_level
            self.add_badge(f"سطح {self.level} 🏅")
            return True
        return False
    
    def check_badges(self, task=None):
        if self.points >= 50 and "50 امتیاز" not in self.badges:
            self.add_badge("50 امتیاز ⭐")
        if self.points >= 100 and "100 امتیاز" not in self.badges:
            self.add_badge("100 امتیاز ⭐⭐")
        if self.streak >= 7 and "هفته اول 🎯" not in self.badges:
            self.add_badge("هفته اول 🎯")
        if self.streak >= 30 and "ماه اول 🌟" not in self.badges:
            self.add_badge("ماه اول 🌟")
        if task and task.get('category') == "کار" and "کارمند نمونه 💼" not in self.badges:
            self.add_badge("کارمند نمونه 💼")
        if task and task.get('category') == "مطالعه" and "دانشجو برتر 📚" not in self.badges:
            self.add_badge("دانشجو برتر 📚")
    
    def add_badge(self, badge):
        if badge not in self.badges:
            self.badges.append(badge)
            self.save()
    
    def get_status(self):
        return {
            'points': self.points,
            'level': self.level,
            'streak': self.streak,
            'badges': self.badges
        }

# ============= کلاس Calendar =============

class PersianCalendar:
    @staticmethod
    def get_persian_date():
        # تبدیل تاریخ میلادی به شمسی
        now = datetime.now()
        return f"{now.year}-{now.month:02d}-{now.day:02d}"
    
    @staticmethod
    def get_persian_month_name(month):
        months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        return months[month - 1] if 1 <= month <= 12 else ""

# ============= صفحه‌های برنامه =============

class TaskPage:
    def __init__(self, page, task_manager, gamification, db):
        self.page = page
        self.task_manager = task_manager
        self.gamification = gamification
        self.db = db
        self.task_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.search_input = ft.TextField(
            hint_text="جستجوی کارها...",
            width=200,
            on_change=self.filter_tasks,
            prefix_icon=ft.icons.SEARCH
        )
        self.filter_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("همه", "all"),
                ft.dropdown.Option("انجام نشده", "pending"),
                ft.dropdown.Option("انجام شده", "done"),
            ],
            value="all",
            width=120,
            on_change=self.filter_tasks
        )
        self.tasks = []
        self.build()
    
    def build(self):
        # نوار بالا
        top_row = ft.Row([
            ft.Text("📋 کارها", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.search_input,
                self.filter_dropdown,
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # دکمه افزودن کار
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=ft.Colors.BLUE_700,
            on_click=lambda _: self.show_add_task_dialog()
        )
        
        # پنل فیلترهای سریع
        quick_filters = ft.Row([
            ft.Chip(
                label=ft.Text("همه"),
                on_click=lambda _: self.apply_filter("all"),
                selected_color=ft.Colors.BLUE_700
            ),
            ft.Chip(
                label=ft.Text("امروز"),
                on_click=lambda _: self.apply_filter("today"),
            ),
            ft.Chip(
                label=ft.Text("این هفته"),
                on_click=lambda _: self.apply_filter("week"),
            ),
            ft.Chip(
                label=ft.Text("بالا اولویت"),
                on_click=lambda _: self.apply_filter("high"),
            ),
        ], spacing=5)
        
        self.content = ft.Column([
            top_row,
            quick_filters,
            ft.Divider(height=10),
            self.task_list,
        ], expand=True)
        
        self.page.add(
            self.content,
            add_button
        )
    
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
        deadline_input = ft.TextField(hint_text="تاریخ سررسید (اختیاری)", rtl=True)
        notes_input = ft.TextField(hint_text="یادداشت (اختیاری)", multiline=True, rtl=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("کار جدید", rtl=True),
            content=ft.Column([
                title_input,
                ft.Row([category_dropdown, priority_dropdown]),
                deadline_input,
                notes_input,
            ], tight=True),
            actions=[
                ft.TextButton("لغو", on_click=lambda _: self.close_dialog()),
                ft.TextButton("افزودن", on_click=lambda _: self.add_task(
                    title_input.value,
                    category_dropdown.value,
                    priority_dropdown.value,
                    deadline_input.value,
                    notes_input.value
                )),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def add_task(self, title, category, priority, deadline, notes):
        if title and title.strip():
            task = self.task_manager.add(title.strip(), category, priority, deadline, None, notes)
            self.gamification.add_points(5, task)
            self.close_dialog()
            self.update_task_list()
            self.page.snack_bar = ft.SnackBar(
                ft.Text("✅ کار جدید اضافه شد!"),
                bgcolor=ft.Colors.GREEN_700
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def close_dialog(self):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def update_task_list(self):
        self.task_list.controls.clear()
        
        for task in self.task_manager.tasks:
            if task['done']:
                continue
            
            priority_colors = {
                "بالا": ft.Colors.RED_700,
                "متوسط": ft.Colors.ORANGE_700,
                "پایین": ft.Colors.GREEN_700
            }
            
            task_card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Checkbox(
                            value=task['done'],
                            on_change=lambda e, t=task: self.toggle_task(t['id']),
                            fill_color=ft.Colors.GREEN_700 if task['done'] else None
                        ),
                        ft.Column([
                            ft.Text(
                                task['title'],
                                size=16,
                                weight=ft.FontWeight.BOLD if not task['done'] else ft.FontWeight.NORMAL,
                                color=ft.Colors.GREY_600 if task['done'] else ft.Colors.BLACK,
                                rtl=True
                            ),
                            ft.Row([
                                ft.Icon(
                                    name=self.get_category_icon(task.get('category', 'سایر')),
                                    size=16,
                                    color=priority_colors.get(task.get('priority', 'متوسط'), ft.Colors.GREY)
                                ),
                                ft.Text(
                                    task.get('category', 'سایر'),
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                    rtl=True
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        task.get('priority', 'متوسط'),
                                        size=10,
                                        color=ft.Colors.WHITE,
                                        rtl=True
                                    ),
                                    bgcolor=priority_colors.get(task.get('priority', 'متوسط'), ft.Colors.GREY),
                                    padding=5,
                                    border_radius=5
                                ),
                                ft.Text(
                                    task.get('created', ''),
                                    size=10,
                                    color=ft.Colors.GREY_500
                                )
                            ])
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                icon_size=20,
                                on_click=lambda e, t=task: self.delete_task(t['id']),
                            )
                        ], spacing=0)
                    ]),
                    padding=10
                )
            )
            self.task_list.controls.append(task_card)
        
        if not self.task_list.controls:
            self.task_list.controls.append(
                ft.Text("🎯 همه کارها انجام شد!", size=16, color=ft.Colors.GREY_500, rtl=True)
            )
        
        self.page.update()
    
    def toggle_task(self, task_id):
        done = self.task_manager.toggle(task_id)
        if done:
            self.gamification.add_points(10)
            self.page.snack_bar = ft.SnackBar(
                ft.Text("🎉 +۱۰ امتیاز! تبریک!"),
                bgcolor=ft.Colors.GREEN_700
            )
            self.page.snack_bar.open = True
        self.update_task_list()
        self.page.update()
    
    def delete_task(self, task_id):
        self.task_manager.delete(task_id)
        self.update_task_list()
        self.page.update()
    
    def filter_tasks(self, e):
        query = self.search_input.value.lower() if self.search_input.value else ""
        filter_type = self.filter_dropdown.value
        
        self.task_list.controls.clear()
        filtered_tasks = self.task_manager.tasks
        
        if query:
            filtered_tasks = [t for t in filtered_tasks if query in t['title'].lower()]
        
        if filter_type == "pending":
            filtered_tasks = [t for t in filtered_tasks if not t['done']]
        elif filter_type == "done":
            filtered_tasks = [t for t in filtered_tasks if t['done']]
        
        for task in filtered_tasks:
            # نمایش کارها
            pass
        self.update_task_list()
    
    def apply_filter(self, filter_type):
        pass
    
    def get_category_icon(self, category):
        icons = {
            "کار": "WORK",
            "شخصی": "PERSON",
            "مطالعه": "SCHOOL",
            "سلامت": "FAVORITE",
            "سایر": "ADD_TASK"
        }
        return icons.get(category, "ADD_TASK")

class DashboardPage:
    def __init__(self, page, task_manager, gamification, timer, db):
        self.page = page
        self.task_manager = task_manager
        self.gamification = gamification
        self.timer = timer
        self.db = db
        self.build()
    
    def build(self):
        stats = self.task_manager.get_stats()
        g_status = self.gamification.get_status()
        
        # کارت آماری
        stat_cards = ft.Row([
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("📋 مجموع", size=12, color=ft.Colors.GREY_600),
                        ft.Text(str(stats['total']), size=24, weight=ft.FontWeight.BOLD),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    width=100
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("✅ انجام شده", size=12, color=ft.Colors.GREY_600),
                        ft.Text(str(stats['done']), size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    width=100
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("⏳ باقی مانده", size=12, color=ft.Colors.GREY_600),
                        ft.Text(str(stats['pending']), size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    width=100
                )
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        # نوار پیشرفت
        progress = ft.Column([
            ft.Text(f"📈 پیشرفت: {stats['completion_rate']:.1f}%", rtl=True),
            ft.ProgressBar(
                value=stats['completion_rate']/100,
                height=10,
                color=ft.Colors.BLUE_700,
                bgcolor=ft.Colors.GREY_300
            )
        ], spacing=5)
        
        # کارت گیمیفیکیشن
        gamification_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🎮 گیمیفیکیشن", size=18, weight=ft.FontWeight.BOLD, rtl=True),
                    ft.Row([
                        ft.Text(f"⭐ امتیاز: {g_status['points']}"),
                        ft.Text(f"🏅 سطح: {g_status['level']}"),
                        ft.Text(f"🔥 رکورد: {g_status['streak']} روز"),
                    ]),
                    ft.Row([
                        ft.Text("🎖️ نشان‌ها: "),
                        ft.Row([ft.Text(badge, size=12, rtl=True) for badge in g_status['badges']])
                    ])
                ]),
                padding=15
            )
        )
        
        # کارت تایمر
        timer_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("⏱️ تایمر پومودورو", size=18, weight=ft.FontWeight.BOLD, rtl=True),
                    ft.Text(self.timer.get_time_string(), size=36, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.IconButton(
                            icon=ft.icons.PLAY_ARROW,
                            on_click=lambda _: self.timer.start(lambda: self.update_timer_display()),
                            icon_color=ft.Colors.GREEN_700
                        ),
                        ft.IconButton(
                            icon=ft.icons.STOP,
                            on_click=lambda _: self.timer.stop(),
                            icon_color=ft.Colors.RED_700
                        ),
                        ft.IconButton(
                            icon=ft.icons.REFRESH,
                            on_click=lambda _: self.timer.reset(),
                            icon_color=ft.Colors.ORANGE_700
                        ),
                    ]),
                    ft.Text(f"جلسات امروز: {self.timer.get_today_sessions()[0]}", rtl=True)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15
            )
        )
        
        # کارهای امروز
        today_tasks = self.task_manager.get_today_tasks()
        today_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"📌 کارهای امروز ({len(today_tasks)})", size=18, weight=ft.FontWeight.BOLD, rtl=True),
                    ft.Column([
                        ft.Text(f"• {task['title']}", rtl=True) for task in today_tasks[:5]
                    ]) if today_tasks else ft.Text("🎉 امروز هیچ کاری نداری!", rtl=True, color=ft.Colors.GREY_500)
                ]),
                padding=15
            )
        )
        
        # کارهای سررسید شده
        upcoming = self.task_manager.get_upcoming_deadlines()
        upcoming_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"⏰ سررسیدهای نزدیک ({len(upcoming)})", size=18, weight=ft.FontWeight.BOLD, rtl=True),
                    ft.Column([
                        ft.Text(f"• {task['title']} ({task.get('deadline', '')})", rtl=True) for task in upcoming[:5]
                    ]) if upcoming else ft.Text("✅ هیچ سررسید نزدیکی نداری!", rtl=True, color=ft.Colors.GREY_500)
                ]),
                padding=15
            )
        )
        
        self.page.add(
            ft.Text("📊 داشبورد", size=24, weight=ft.FontWeight.BOLD),
            stat_cards,
            progress,
            gamification_card,
            timer_card,
            today_card,
            upcoming_card,
        )
    
    def update_timer_display(self):
        # به‌روزرسانی نمایش تایمر
        pass

class CalendarPage:
    def __init__(self, page, task_manager, db):
        self.page = page
        self.task_manager = task_manager
        self.db = db
        self.selected_date = datetime.now().strftime("%Y-%m-%d")
        self.build()
    
    def build(self):
        # تقویم ساده با تاریخ امروز
        today = datetime.now()
        persian_date = PersianCalendar.get_persian_date()
        persian_month = PersianCalendar.get_persian_month_name(today.month)
        
        self.page.add(
            ft.Text("📅 تقویم", size=24, weight=ft.FontWeight.BOLD),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"تاریخ امروز: {persian_date}", size=18, rtl=True),
                        ft.Text(f"{today.year} {persian_month} {today.day}", size=16, rtl=True),
                        ft.Divider(height=10),
                        ft.Text("📌 کارهای امروز", size=16, weight=ft.FontWeight.BOLD, rtl=True),
                        self.tasks_container()
                    ]),
                    padding=15
                )
            )
        )
    
    def tasks_container(self):
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = [t for t in self.task_manager.tasks if t.get('created') == today]
        
        return ft.Column([
            ft.Column([
                ft.Text(f"• {task['title']}", rtl=True) for task in tasks
            ]) if tasks else ft.Text("📭 هیچ کاری در این تاریخ نیست!", rtl=True, color=ft.Colors.GREY_500)
        ])

class SettingsPage:
    def __init__(self, page, db):
        self.page = page
        self.db = db
        self.build()
    
    def build(self):
        theme_toggle = ft.Switch(
            value=self.page.theme_mode == ft.ThemeMode.DARK,
            on_change=self.toggle_theme,
            label="حالت شب"
        )
        
        backup_button = ft.ElevatedButton(
            "📥 پشتیبان‌گیری",
            on_click=self.backup_data
        )
        
        restore_button = ft.ElevatedButton(
            "📤 بازیابی",
            on_click=self.restore_data
        )
        
        self.page.add(
            ft.Text("⚙️ تنظیمات", size=24, weight=ft.FontWeight.BOLD),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("ظاهر", size=18, weight=ft.FontWeight.BOLD),
                        theme_toggle,
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("داده‌ها", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([backup_button, restore_button]),
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("📊 آمار پیشرفته", size=18, weight=ft.FontWeight.BOLD, rtl=True),
                        ft.Text("تعداد کل کارها: ...", rtl=True),
                        ft.Text("میانگین کارهای روزانه: ...", rtl=True),
                        ft.Text("بیشترین دسته بندی: ...", rtl=True),
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
        shutil.copy('tasks.db', f'tasks_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        self.page.snack_bar = ft.SnackBar(
            ft.Text("✅ پشتیبان‌گیری انجام شد!"),
            bgcolor=ft.Colors.GREEN_700
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def restore_data(self):
        self.page.snack_bar = ft.SnackBar(
            ft.Text("⚠️ این قابلیت در حال توسعه است!"),
            bgcolor=ft.Colors.ORANGE_700
        )
        self.page.snack_bar.open = True
        self.page.update()

# ============= صفحه اصلی (با ناوبری) =============

async def main(page: ft.Page):
    page.title = "مدیریت زمان حرفه‌ای"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 10
    page.rtl = True
    page.bgcolor = ft.Colors.GREY_50
    
    # راه‌اندازی دیتابیس و کلاس‌ها
    db = Database()
    task_manager = TaskManager(db)
    gamification = Gamification(db)
    timer = PomodoroTimer(page, db)
    
    # ایجاد صفحه‌ها
    task_page = TaskPage(page, task_manager, gamification, db)
    dashboard_page = DashboardPage(page, task_manager, gamification, timer, db)
    calendar_page = CalendarPage(page, task_manager, db)
    settings_page = SettingsPage(page, db)
    
    # ناوبری با Bottom Navigation
    def change_page(e):
        page.controls.clear()
        page.add(nav_bar)
        
        if e.control.selected_index == 0:
            page.add(dashboard_page.content if hasattr(dashboard_page, 'content') else dashboard_page)
        elif e.control.selected_index == 1:
            task_page.update_task_list()
            page.add(task_page.content)
        elif e.control.selected_index == 2:
            page.add(calendar_page)
        elif e.control.selected_index == 3:
            page.add(settings_page)
        page.update()
    
    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon=ft.icons.DASHBOARD, label="داشبورد"),
            ft.NavigationDestination(icon=ft.icons.LIST_ALT, label="کارها"),
            ft.NavigationDestination(icon=ft.icons.CALENDAR_MONTH, label="تقویم"),
            ft.NavigationDestination(icon=ft.icons.SETTINGS, label="تنظیمات"),
        ],
        selected_index=0,
        on_change=change_page,
        bgcolor=ft.Colors.WHITE,
        elevation=5
    )
    
    # صفحه پیش‌فرض
    page.add(nav_bar)
    page.add(dashboard_page.content if hasattr(dashboard_page, 'content') else dashboard_page)
    page.update()

ft.app(target=main, assets_dir="assets")

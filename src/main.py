import flet as ft
import json
import os
import threading
import time
from datetime import datetime, timedelta
import sqlite3

# ============= دیتابیس =============

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('lovely_tasks.db')
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
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
                notes TEXT,
                energy_level TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                last_done TEXT,
                created TEXT
            )
        ''')
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_energy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                energy_level TEXT
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
                'notes': row[8],
                'energy_level': row[9]
            })
    
    def add(self, title, category="سایر", priority="متوسط", eisenhower_type="مهم و غیر فوری", 
            deadline=None, notes="", energy_level="متوسط"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.execute(
            '''INSERT INTO tasks 
            (title, category, priority, eisenhower_type, deadline, created, notes, energy_level) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, category, priority, eisenhower_type, deadline, now, notes, energy_level)
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
        return {
            'total': total,
            'done': done,
            'pending': total - done,
            'completion_rate': (done / total * 100) if total > 0 else 0
        }
    
    def get_today_tasks(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return [t for t in self.tasks if not t['done']]
    
    def get_tasks_by_eisenhower(self, eisenhower_type):
        return [t for t in self.tasks if t.get('eisenhower_type') == eisenhower_type and not t['done']]

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
            self.add_badge(f"سطح {self.level} 🏅")
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
                'streak': row[2],
                'last_done': row[3],
                'created': row[4]
            })
    
    def add(self, name):
        now = datetime.now().strftime("%Y-%m-%d")
        self.db.execute(
            'INSERT INTO habits (name, created) VALUES (?, ?)',
            (name, now)
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

# ============= اپلیکیشن اصلی با طراحی عاشقانه =============

async def main(page: ft.Page):
    # تنظیمات صفحه
    page.title = "💖 مدیریت زمان عاشقانه"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 15
    page.rtl = True
    page.bgcolor = ft.Colors.PINK_50
    
    # راه‌اندازی دیتابیس
    db = Database()
    task_manager = TaskManager(db)
    gamification = Gamification(db)
    habit_manager = HabitManager(db)
    
    # ===== صفحه داشبورد =====
    def create_dashboard():
        stats = task_manager.get_stats()
        g_status = gamification.get_status()
        
        # هدر عاشقانه
        header = ft.Container(
            content=ft.Column([
                ft.Text("💖 عشق من، امروز چطور می‌خواهی وقتت رو مدیریت کنی؟", 
                       size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700, rtl=True),
                ft.Text(f"🌸 امروز {stats['total']} کار داری، {stats['done']} تاش رو انجام دادی!", 
                       size=16, color=ft.Colors.PURPLE_600, rtl=True),
            ]),
            padding=10,
            bgcolor=ft.Colors.PINK_100,
            border_radius=10
        )
        
        # کارت‌های آماری با طراحی عاشقانه
        cards = ft.Row([
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("💝", size=30),
                        ft.Text(f"{stats['total']}", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("کارها", size=12, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15, width=90, bgcolor=ft.Colors.PINK_50, border_radius=15
                ),
                elevation=3
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("✅", size=30),
                        ft.Text(f"{stats['done']}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                        ft.Text("انجام شده", size=12, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15, width=90, bgcolor=ft.Colors.GREEN_50, border_radius=15
                ),
                elevation=3
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("⏳", size=30),
                        ft.Text(f"{stats['pending']}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                        ft.Text("باقی‌مانده", size=12, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15, width=90, bgcolor=ft.Colors.ORANGE_50, border_radius=15
                ),
                elevation=3
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        # نوار پیشرفت
        progress = ft.Container(
            content=ft.Column([
                ft.Text(f"💕 پیشرفت عشق: {stats['completion_rate']:.1f}%", rtl=True, 
                       color=ft.Colors.PINK_700, weight=ft.FontWeight.BOLD),
                ft.ProgressBar(
                    value=stats['completion_rate']/100,
                    height=12,
                    color=ft.Colors.PINK_700,
                    bgcolor=ft.Colors.PINK_100
                )
            ]),
            padding=10
        )
        
        # کارت گیمیفیکیشن عاشقانه
        gamification_card = ft.Card(
            ft.Container(
                ft.Column([
                    ft.Row([
                        ft.Text("⭐", size=30),
                        ft.Text(f"{g_status['points']} امتیاز", size=18, weight=ft.FontWeight.BOLD, 
                               color=ft.Colors.PINK_700),
                        ft.Text(f"🏅 سطح {g_status['level']}", size=16, color=ft.Colors.PURPLE_600),
                    ]),
                    ft.Row([
                        ft.Text(f"🔥 {g_status['streak']} روز پشت سر هم", size=14, color=ft.Colors.ORANGE_700),
                        ft.Text(f"💪 {g_status['total_focus_time']} دقیقه تمرکز", size=14, color=ft.Colors.BLUE_700),
                    ]),
                    ft.Row([
                        ft.Text("🎖️ نشان‌ها:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([ft.Text(badge, size=14, color=ft.Colors.PINK_700) for badge in g_status['badges']])
                    ]) if g_status['badges'] else ft.Text("💝 هنوز نشان خاصی نداری، ادامه بده!", 
                                                          color=ft.Colors.GREY_600)
                ]),
                padding=15, bgcolor=ft.Colors.PINK_50
            ),
            elevation=3
        )
        
        return ft.Column([
            header,
            ft.Divider(height=10, color=ft.Colors.PINK_200),
            cards,
            progress,
            gamification_card,
        ])
    
    # ===== صفحه کارها =====
    task_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def add_task_dialog():
        title_input = ft.TextField(
            hint_text="💭 چکار می‌خواهی انجام بدی؟", 
            rtl=True,
            border_color=ft.Colors.PINK_400,
            focused_border_color=ft.Colors.PINK_700,
            prefix_icon="💝"
        )
        category_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("💼 کار", "کار"),
                ft.dropdown.Option("🏠 شخصی", "شخصی"),
                ft.dropdown.Option("📚 مطالعه", "مطالعه"),
                ft.dropdown.Option("💪 سلامتی", "سلامت"),
            ],
            value="کار",
            rtl=True,
            bgcolor=ft.Colors.PINK_50
        )
        priority_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("🔥 بالا", "بالا"),
                ft.dropdown.Option("⭐ متوسط", "متوسط"),
                ft.dropdown.Option("🌱 پایین", "پایین"),
            ],
            value="متوسط",
            rtl=True,
            bgcolor=ft.Colors.PINK_50
        )
        eisenhower_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("🔴 مهم و فوری", "مهم و فوری"),
                ft.dropdown.Option("🟡 مهم و غیر فوری", "مهم و غیر فوری"),
                ft.dropdown.Option("🟠 غیر مهم و فوری", "غیر مهم و فوری"),
                ft.dropdown.Option("⚪ حذف‌شدنی", "حذف‌شدنی"),
            ],
            value="مهم و غیر فوری",
            rtl=True,
            bgcolor=ft.Colors.PINK_50
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text("💖 کار جدید", rtl=True, color=ft.Colors.PINK_700),
            content=ft.Column([
                title_input,
                ft.Row([category_dropdown, priority_dropdown]),
                eisenhower_dropdown,
            ], tight=True),
            actions=[
                ft.TextButton("❌ لغو", on_click=lambda _: close_dialog()),
                ft.TextButton("💕 افزودن", on_click=lambda _: add_task(
                    title_input.value,
                    category_dropdown.value,
                    priority_dropdown.value,
                    eisenhower_dropdown.value
                )),
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def close_dialog():
        if page.dialog:
            page.dialog.open = False
            page.update()
    
    def add_task(title, category, priority, eisenhower):
        if title and title.strip():
            task_manager.add(title.strip(), category, priority, eisenhower)
            gamification.add_points(5)
            close_dialog()
            update_task_list()
            page.snack_bar = ft.SnackBar(
                ft.Text("💕 کار جدید اضافه شد! +۵ امتیاز عشق"),
                bgcolor=ft.Colors.PINK_700
            )
            page.snack_bar.open = True
            page.update()
    
    def update_task_list():
        task_list.controls.clear()
        
        for task in task_manager.tasks:
            if task['done']:
                continue
            
            priority_icons = {
                "بالا": "🔥",
                "متوسط": "⭐",
                "پایین": "🌱"
            }
            priority_colors = {
                "بالا": ft.Colors.RED_400,
                "متوسط": ft.Colors.ORANGE_400,
                "پایین": ft.Colors.GREEN_400
            }
            
            task_card = ft.Card(
                ft.Container(
                    ft.Row([
                        ft.Checkbox(
                            value=task['done'],
                            on_change=lambda e, t=task: toggle_task(t['id']),
                            fill_color=ft.Colors.PINK_700,
                            check_color=ft.Colors.WHITE
                        ),
                        ft.Column([
                            ft.Text(
                                f"{priority_icons.get(task.get('priority', 'متوسط'), '⭐')} {task['title']}", 
                                size=16, weight=ft.FontWeight.BOLD, rtl=True
                            ),
                            ft.Row([
                                ft.Text(task.get('category', ''), size=12, color=ft.Colors.GREY_600),
                                ft.Container(
                                    ft.Text(task.get('eisenhower_type', ''), size=10, color=ft.Colors.WHITE),
                                    bgcolor=ft.Colors.PINK_400,
                                    padding=5,
                                    border_radius=5
                                ),
                            ])
                        ], expand=True),
                        ft.IconButton(
                            icon="💔",
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda e, t=task: delete_task(t['id'])
                        )
                    ]),
                    padding=10
                ),
                elevation=2
            )
            task_list.controls.append(task_card)
        
        if not task_list.controls:
            task_list.controls.append(
                ft.Text("💖 همه کارها انجام شد! امروز عالی بودی!", 
                       size=16, color=ft.Colors.PINK_500, rtl=True)
            )
        page.update()
    
    def toggle_task(task_id):
        done = task_manager.toggle(task_id)
        if done:
            gamification.add_points(10)
            page.snack_bar = ft.SnackBar(
                ft.Text("🎉 +۱۰ امتیاز عشق! به خودت افتخار کن!"),
                bgcolor=ft.Colors.PINK_700
            )
            page.snack_bar.open = True
        update_task_list()
        page.update()
    
    def delete_task(task_id):
        task_manager.delete(task_id)
        update_task_list()
        page.update()
    
    def create_tasks_page():
        return ft.Column([
            ft.Row([
                ft.Text("💕 کارهای روزانه", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700),
                ft.IconButton(
                    icon="💝",
                    icon_size=30,
                    icon_color=ft.Colors.PINK_700,
                    on_click=lambda _: add_task_dialog()
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.PINK_200),
            task_list,
        ])
    
    # ===== صفحه عادت‌ها =====
    habit_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def add_habit_dialog():
        name_input = ft.TextField(hint_text="💪 عادت جدید...", rtl=True, border_color=ft.Colors.PINK_400)
        
        dialog = ft.AlertDialog(
            title=ft.Text("💖 عادت جدید", rtl=True, color=ft.Colors.PINK_700),
            content=ft.Column([name_input], tight=True),
            actions=[
                ft.TextButton("❌ لغو", on_click=lambda _: close_habit_dialog()),
                ft.TextButton("💕 افزودن", on_click=lambda _: add_habit(name_input.value)),
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def close_habit_dialog():
        if page.dialog:
            page.dialog.open = False
            page.update()
    
    def add_habit(name):
        if name and name.strip():
            habit_manager.add(name.strip())
            gamification.add_points(10)
            close_habit_dialog()
            update_habit_list()
            page.snack_bar = ft.SnackBar(
                ft.Text("💪 عادت جدید اضافه شد! +۱۰ امتیاز عشق"),
                bgcolor=ft.Colors.PINK_700
            )
            page.snack_bar.open = True
            page.update()
    
    def update_habit_list():
        habit_list.controls.clear()
        
        for habit in habit_manager.habits:
            habit_card = ft.Card(
                ft.Container(
                    ft.Row([
                        ft.Text(f"💪 {habit['name']}", size=16, rtl=True),
                        ft.Row([
                            ft.Text(f"🔥 {habit['streak']} روز", size=14, color=ft.Colors.ORANGE_700),
                            ft.IconButton(
                                icon="✅",
                                icon_color=ft.Colors.GREEN_700,
                                on_click=lambda e, h=habit: mark_habit_done(h['id'])
                            )
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10
                ),
                elevation=2
            )
            habit_list.controls.append(habit_card)
        
        if not habit_list.controls:
            habit_list.controls.append(
                ft.Text("💝 هنوز عادتی نداری، یه عادت جدید بساز!", 
                       size=16, color=ft.Colors.PINK_500, rtl=True)
            )
        page.update()
    
    def mark_habit_done(habit_id):
        habit_manager.mark_done(habit_id)
        gamification.add_points(5)
        update_habit_list()
        page.snack_bar = ft.SnackBar(
            ft.Text("💪 عادت ثبت شد! +۵ امتیاز عشق"),
            bgcolor=ft.Colors.PINK_700
        )
        page.snack_bar.open = True
        page.update()
    
    def create_habits_page():
        return ft.Column([
            ft.Row([
                ft.Text("💪 عادت‌های من", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700),
                ft.IconButton(
                    icon="💝",
                    icon_size=30,
                    icon_color=ft.Colors.PINK_700,
                    on_click=lambda _: add_habit_dialog()
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.PINK_200),
            habit_list,
        ])
    
    # ===== صفحه پومودورو =====
    def create_pomodoro_page():
        timer_display = ft.Text("25:00", size=60, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700)
        is_running = False
        is_work = True
        remaining = 25 * 60
        sessions = 0
        
        def update_display():
            minutes = remaining // 60
            seconds = remaining % 60
            timer_display.value = f"{minutes:02d}:{seconds:02d}"
            timer_display.update()
        
        def start_timer(e):
            nonlocal is_running
            if not is_running:
                is_running = True
                thread = threading.Thread(target=run_timer, daemon=True)
                thread.start()
        
        def run_timer():
            nonlocal remaining, is_running, is_work, sessions
            while is_running and remaining > 0:
                time.sleep(1)
                remaining -= 1
                update_display()
            
            if remaining == 0 and is_running:
                sessions += 1
                gamification.add_points(10)
                is_work = not is_work
                remaining = 25 * 60 if is_work else 5 * 60
                update_display()
                page.snack_bar = ft.SnackBar(
                    ft.Text("💕 زمان استراحت!" if not is_work else "💕 زمان تمرکز!"),
                    bgcolor=ft.Colors.PINK_700
                )
                page.snack_bar.open = True
                page.update()
                start_timer(None)
        
        return ft.Column([
            ft.Text("🍅 پومودورو عاشقانه", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700),
            ft.Divider(color=ft.Colors.PINK_200),
            ft.Container(
                ft.Column([
                    timer_display,
                    ft.Text(f"🌸 {sessions} جلسه امروز", size=16, color=ft.Colors.PURPLE_600),
                    ft.Row([
                        ft.IconButton(
                            icon="▶️",
                            icon_size=40,
                            icon_color=ft.Colors.PINK_700,
                            on_click=start_timer
                        ),
                        ft.IconButton(
                            icon="⏹️",
                            icon_size=40,
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda _: stop_timer()
                        ),
                        ft.IconButton(
                            icon="🔄",
                            icon_size=40,
                            icon_color=ft.Colors.ORANGE_400,
                            on_click=lambda _: reset_timer()
                        ),
                    ]),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=30,
                bgcolor=ft.Colors.PINK_50,
                border_radius=20
            ),
            ft.Text("💝 ۲۵ دقیقه تمرکز + ۵ دقیقه استراحت = عشق به خودت", 
                   size=14, color=ft.Colors.PINK_600, rtl=True)
        ])
    
    # ===== صفحه تنظیمات =====
    def create_settings_page():
        theme_toggle = ft.Switch(
            value=False,
            on_change=lambda e: toggle_theme(e),
            label="🌙 حالت شب"
        )
        
        backup_button = ft.ElevatedButton(
            "💾 پشتیبان‌گیری از عشق‌ها",
            on_click=lambda _: backup_data(),
            bgcolor=ft.Colors.PINK_700,
            color=ft.Colors.WHITE
        )
        
        return ft.Column([
            ft.Text("⚙️ تنظیمات", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_700),
            ft.Divider(color=ft.Colors.PINK_200),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("💕 ظاهر", size=18, weight=ft.FontWeight.BOLD),
                        theme_toggle,
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("💾 پشتیبان‌گیری", size=18, weight=ft.FontWeight.BOLD),
                        backup_button,
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column([
                        ft.Text("💖 درباره", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("مدیریت زمان عاشقانه v3.0", size=14),
                        ft.Text("با عشق برای عزیزان ساخته شده", size=12, color=ft.Colors.PINK_600),
                    ]),
                    padding=15
                )
            ),
        ])
    
    def toggle_theme(e):
        if e.control.value:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = ft.Colors.GREY_900
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = ft.Colors.PINK_50
        page.update()
    
    def backup_data():
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy('lovely_tasks.db', f'love_backup_{timestamp}.db')
        page.snack_bar = ft.SnackBar(
            ft.Text("💕 پشتیبان‌گیری از عشق‌ها انجام شد!"),
            bgcolor=ft.Colors.PINK_700
        )
        page.snack_bar.open = True
        page.update()
    
    # ===== ناوبری اصلی =====
    def change_page(e):
        page.controls.clear()
        page.add(nav_bar)
        
        pages = [create_dashboard, create_tasks_page, create_habits_page, create_pomodoro_page, create_settings_page]
        page.add(pages[e.control.selected_index]())
        page.update()
    
    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon="💖", label="خانه"),
            ft.NavigationDestination(icon="📋", label="کارها"),
            ft.NavigationDestination(icon="💪", label="عادت‌ها"),
            ft.NavigationDestination(icon="🍅", label="پومودورو"),
            ft.NavigationDestination(icon="⚙️", label="تنظیمات"),
        ],
        selected_index=0,
        on_change=change_page,
        bgcolor=ft.Colors.WHITE,
        elevation=5
    )
    
    page.add(nav_bar)
    page.add(create_dashboard())
    update_task_list()
    update_habit_list()
    page.update()

ft.app(target=main)

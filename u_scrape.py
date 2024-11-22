import os
import sqlite3
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
from ttkthemes import ThemedTk
import csv
from cryptography.fernet import Fernet
import webbrowser
import matplotlib.pyplot as plt
import threading
import schedule
import time


YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
API_KEY_FILE = "api_key.enc"
ENCRYPTION_KEY_FILE = "encryption.key"

class YouTubeScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("U-Scrape")
        self.root.geometry("800x700")
        self.api_key = tk.StringVar()
        self.selected_country = tk.StringVar()
        self.max_results = tk.IntVar(value=50)
        self.progress = tk.IntVar()
        self.running = True

        threading.Thread(target=self.run_scheduler, daemon=True).start()

        self.countries = {
            "United States": "US",
            "Canada": "CA",
            "United Kingdom": "GB",
            "India": "IN",
            "Australia": "AU",
            "Germany": "DE",
            "France": "FR",
        }

        self.encryption_key = self.get_encryption_key()
        self.db_path = "youtube_data.db"
        self.setup_database()
        self.setup_ui()
        self.load_api_key()


    def run_scheduler(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def get_encryption_key(self):
        if not os.path.exists(ENCRYPTION_KEY_FILE):
            key = Fernet.generate_key()
            with open(ENCRYPTION_KEY_FILE, "wb") as key_file:
                key_file.write(key)
        else:
            with open(ENCRYPTION_KEY_FILE, "rb") as key_file:
                key = key_file.read()
        return key

    def setup_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    title TEXT,
                    published_at TEXT,
                    channel_title TEXT,
                    view_count INTEGER,
                    like_count INTEGER,
                    comment_count INTEGER,
                    country TEXT  -- Add this line
                )
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred while setting up the database: {e}")

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="API Key:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.api_key, width=60).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="Save API Key", command=self.save_api_key).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame, text="Country:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        country_menu = ttk.Combobox(frame, textvariable=self.selected_country, values=list(self.countries.keys()), state="readonly")
        country_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        country_menu.set("United States")

        ttk.Label(frame, text="Duplicate Handling:").grid(row=2, column=1, sticky="e", padx=5, pady=5)
        self.duplicate_handling = tk.StringVar(value="skip")  # Default to 'skip'

        radio_skip = ttk.Radiobutton(frame, text="Skip", variable=self.duplicate_handling, value="skip")
        radio_skip.grid(row=2, column=2, sticky="e")

        radio_overwrite = ttk.Radiobutton(frame, text="Overwrite", variable=self.duplicate_handling, value="overwrite")
        radio_overwrite.grid(row=2, column=3, sticky="e")

        radio_ignore = ttk.Radiobutton(frame, text="Ignore                         ", variable=self.duplicate_handling, value="ignore")
        radio_ignore.grid(row=2, column=4, sticky="e")

        
        ttk.Label(frame, text="Max Results per Scrape (1-50):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Spinbox(frame, from_=1, to=50, textvariable=self.max_results, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.log_box = tk.Text(frame, height=10, state="disabled")
        self.log_box.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        ttk.Button(frame, text="Start Scraping", command=self.start_scraping).grid(row=5, column=0, columnspan=3, pady=10)
        ttk.Button(frame, text="Export to CSV", command=self.export_to_csv).grid(row=6, column=0, columnspan=3, pady=10)
        ttk.Button(frame, text="View Database", command=self.open_database_window).grid(row=7, column=0, columnspan=3, pady=10)
        ttk.Button(frame, text="Visualize Data", command=self.open_visualization_window).grid(row=8, column=0, columnspan=3, pady=10)
        ttk.Button(frame, text="Schedule Scraping", command=self.schedule_scraping_window).grid(row=8, column=0, columnspan=3, pady=10)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

    def schedule_scraping_window(self):
        """Opens a window to schedule scraping tasks."""
        schedule_window = tk.Toplevel(self.root)
        schedule_window.title("Schedule Scraping")
        schedule_window.geometry("400x200")

        ttk.Label(schedule_window, text="Scrape every (minutes):").grid(row=0, column=0, padx=5, pady=5)
        interval_var = tk.IntVar(value=10)  # Default to 10 minutes
        ttk.Spinbox(schedule_window, from_=1, to=1440, textvariable=interval_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(schedule_window, text="Set Schedule", command=lambda: self.set_schedule(interval_var.get())).grid(row=1, column=0, columnspan=2, pady=10)

    def set_schedule(self, interval):
        schedule.every(interval).minutes.do(self.scheduled_scraping_task)
        messagebox.showinfo("Schedule Set", f"Scraping scheduled every {interval} minutes.")

    def scheduled_scraping_task(self):
        try:
            self.start_scraping()
            self.log("Scheduled scraping completed successfully.")
        except Exception as e:
            self.log(f"Scheduled scraping failed: {str(e)}")


    def log(self, message):
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.config(state="disabled")
        self.log_box.see("end")

    def save_api_key(self):
        api_key = self.api_key.get().strip()
        if not api_key:
            messagebox.showerror("Error", "API key cannot be empty.")
            return

        try:
            fernet = Fernet(self.encryption_key)
            encrypted_key = fernet.encrypt(api_key.encode())
            with open(API_KEY_FILE, "wb") as file:
                file.write(encrypted_key)
            messagebox.showinfo("Success", "API Key saved and encrypted successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to encrypt API Key: {e}")

    def load_api_key(self):
        if os.path.exists(API_KEY_FILE):
            try:
                fernet = Fernet(self.encryption_key)
                with open(API_KEY_FILE, "rb") as file:
                    encrypted_key = file.read()
                decrypted_key = fernet.decrypt(encrypted_key).decode()
                self.api_key.set(decrypted_key)
                self.log("API Key loaded successfully.")
            except Exception as e:
                self.log(f"Failed to decrypt API Key: {e}")

    def start_scraping(self):
        api_key = self.api_key.get().strip()
        country_name = self.selected_country.get()
        country_code = self.countries.get(country_name)
        max_results = self.max_results.get()

        if not api_key:
            messagebox.showerror("Error", "Please provide a valid API key.")
            return

        if not country_code:
            messagebox.showerror("Error", "Please select a valid country.")
            return

        if not (1 <= max_results <= 50):
            messagebox.showerror("Error", "Max results must be between 1 and 50.")
            return

        try:
            self.log("Starting data scraping...")
            self.progress.set(0)
            self.root.update_idletasks()

            country_data = self.scrape_data(api_key, country_code, max_results)
            self.save_data_to_db(country_data)

            self.progress.set(100)
            self.log("Data scraping completed!")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

    def scrape_data(self, api_key, country_code, max_results):
        params = {
            "part": "id,snippet,statistics",
            "chart": "mostPopular",
            "regionCode": country_code,
            "maxResults": max_results,
            "key": api_key,
        }
        response = requests.get(YOUTUBE_API_URL, params=params)

        if response.status_code != 200:
            error_message = response.json().get("error", {}).get("message", "Unknown Error")
            raise Exception(f"API Error: {error_message}")

        data = response.json()
        videos = []
        for item in data.get("items", []):
            video = {
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "published_at": item["snippet"]["publishedAt"],
                "channel_title": item["snippet"]["channelTitle"],
                "view_count": int(item["statistics"].get("viewCount", 0)),
                "like_count": int(item["statistics"].get("likeCount", 0)),
                "comment_count": int(item["statistics"].get("commentCount", 0)),
                "country": country_code
            }
            videos.append(video)

        self.log(f"Fetched {len(videos)} videos for country: {country_code}")
        return videos

    def open_visualization_window(self):
        vis_window = Toplevel(self.root)
        vis_window.title("Data Visualization")
        vis_window.geometry("400x300")

        ttk.Label(vis_window, text="Select Visualization Type:").pack(pady=10)


        ttk.Button(vis_window, text="Top Channels by Views", command=self.plot_top_channels).pack(fill="x", padx=20, pady=5)
        ttk.Button(vis_window, text="Videos by Country", command=self.plot_country_distribution).pack(fill="x", padx=20, pady=5)
        ttk.Button(vis_window, text="Views Over Time", command=self.plot_view_trends).pack(fill="x", padx=20, pady=5)

    def plot_top_channels(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT channel_title, SUM(view_count) as total_views
            FROM videos
            GROUP BY channel_title
            ORDER BY total_views DESC
            LIMIT 10
        """)
        data = cursor.fetchall()
        conn.close()

        channels = [row[0] for row in data]
        views = [row[1] for row in data]

        plt.figure(figsize=(10, 6))
        plt.barh(channels, views, color='skyblue')
        plt.xlabel("Total Views")
        plt.ylabel("Channel")
        plt.title("Top 10 Channels by Views")
        plt.gca().invert_yaxis()  # Invert y-axis for better readability
        plt.tight_layout()
        plt.show()

    def plot_country_distribution(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT country, COUNT(*) as video_count
            FROM videos
            GROUP BY country
        """)
        data = cursor.fetchall()
        conn.close()

        countries = [row[0] for row in data]
        counts = [row[1] for row in data]

        plt.figure(figsize=(8, 8))
        plt.pie(counts, labels=countries, autopct="%1.1f%%", startangle=140)
        plt.title("Distribution of Videos by Country")
        plt.show()

    def plot_view_trends(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(published_at) as date, SUM(view_count) as total_views
            FROM videos
            GROUP BY date
            ORDER BY date
        """)
        data = cursor.fetchall()
        conn.close()

        dates = [row[0] for row in data]
        views = [row[1] for row in data]

        plt.figure(figsize=(10, 6))
        plt.plot(dates, views, marker="o", linestyle="-", color="b")
        plt.xlabel("Date")
        plt.ylabel("Total Views")
        plt.title("Video Views Over Time")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    
    def save_data_to_db(self, data):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for video in data:
            # Check for duplicates
            cursor.execute("SELECT * FROM videos WHERE video_id = ?", (video["video_id"],))
            existing_record = cursor.fetchone()

            if existing_record:
                if self.duplicate_handling.get() == "skip":
                    # Skip duplicate record
                    self.log(f"Skipped duplicate record for Video ID {video['video_id']}.")
                    continue
                elif self.duplicate_handling.get() == "overwrite":
                    # Overwrite existing record
                    cursor.execute("""
                        UPDATE videos
                        SET title = :title, 
                            published_at = :published_at, 
                            channel_title = :channel_title,
                            view_count = :view_count,
                            like_count = :like_count,
                            comment_count = :comment_count,
                            country = :country
                        WHERE video_id = :video_id
                    """, video)
                    self.log(f"Overwrote duplicate record for Video ID {video['video_id']}.")
                elif self.duplicate_handling.get() == "ignore":
                    # Ignore duplicate check and insert as a new record
                    cursor.execute("""
                        INSERT INTO videos (video_id, title, published_at, channel_title, view_count, like_count, comment_count, country)
                        VALUES (:video_id, :title, :published_at, :channel_title, :view_count, :like_count, :comment_count, :country)
                    """, video)
                    self.log(f"Ignored duplicate and added new record for Video ID {video['video_id']}.")
            else:
                # Insert new record if no duplicate is found
                cursor.execute("""
                    INSERT INTO videos (video_id, title, published_at, channel_title, view_count, like_count, comment_count, country)
                    VALUES (:video_id, :title, :published_at, :channel_title, :view_count, :like_count, :comment_count, :country)
                """, video)

        conn.commit()
        conn.close()
        self.log("Data saved to the database.")
    except sqlite3.Error as e:
        raise Exception(f"Database Error: {e}")


    def export_to_csv(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            messagebox.showinfo("Info", "No data available to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Video ID", "Title", "Published At", "Channel Title", "View Count", "Like Count", "Comment Count"])
            writer.writerows(rows)

        self.log(f"Data exported to {file_path}")
        messagebox.showinfo("Success", "Data exported successfully!")

    def open_database_window(self):
        db_window = tk.Toplevel(self.root)
        db_window.title("Database Viewer")
        db_window.geometry("900x500")

        frame = ttk.Frame(db_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(frame, columns=("video_id", "title", "published_at", "channel_title", "view_count", "like_count", "comment_count"), show="headings", height=15)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        columns = {
            "video_id": "Video ID",
            "title": "Title",
            "published_at": "Published At",
            "channel_title": "Channel Title",
            "view_count": "Views",
            "like_count": "Likes",
            "comment_count": "Comments",
        }

        for col, heading in columns.items():
            tree.heading(col, text=heading)
            tree.column(col, width=120, anchor="center")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT video_id, title, published_at, channel_title, view_count, like_count, comment_count FROM videos")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            tree.insert("", "end", values=row)

        ttk.Button(db_window, text="Refresh", command=lambda: self.refresh_treeview(tree)).pack(side="left", padx=10, pady=10)
        ttk.Button(db_window, text="Play Video", command=lambda: self.play_video(tree)).pack(side="left", padx=10, pady=10)

    def play_video(self, tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "No video selected.")
            return

        video_id = tree.item(selected_item[0], "values")[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        webbrowser.open(video_url)
    def refresh_treeview(self, tree):
        for item in tree.get_children():
            tree.delete(item)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT video_id, title, published_at, channel_title, view_count, like_count, comment_count FROM videos")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            tree.insert("", "end", values=row)


if __name__ == "__main__":
    root = ThemedTk(theme="superhero")
    app = YouTubeScraperApp(root)
    root.mainloop()

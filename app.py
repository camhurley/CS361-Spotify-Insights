import os
import tkinter as tk  # https://docs.python.org/3/library/tk.html
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import spotipy  # https://spotipy.readthedocs.io/en/2.25.0/
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Spotify API environment loading
load_dotenv('auth.env')
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# Spotipy's scope. CHECK HERE IF THERE'S PERMISSION ERRORS
SCOPE = "user-read-recently-played user-read-currently-playing user-read-playback-state"

# Functions

def connect_to_spotify():
    """
    Connects to Spotify using Spotipy and returns a Spotify client instance.
    """
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE
        )
    )
    return sp


def get_current_track(sp):
    """
    Returns last played song, by the last played artist, with the last played album cover
    """

    # Defining our currently-playing track
    current = sp.current_user_playing_track()

    if current and current.get('item'):
        track = current['item']
        title = track['name']
        artist = ", ".join([artist['name'] for artist in track['artists']])
        album_images = track['album'].get('images', [])
        album_cover_url = album_images[0]['url'] if album_images else None
    else:
        title = None
        artist = None
        album_cover_url = None

    return title, artist, album_cover_url


def get_user_location():
    """
    Simple IP-based geolocation lookup.
    Returns the user's city, or 'Unknown' if it fails.
    """
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        city = data.get("city", "Unknown")
        return city
    except Exception as e:
        print(f"Geolocation error: {e}")
        return "Unknown"


# Main UI (Tkinter is kinda cool but kinda brutal lol)

def show_login_screen():
    """
    Start page with a login button (even if .cache exists on the local copy already)
    """

    login_window = tk.Tk()
    login_window.title("Spotify Insights")
    login_window.geometry("300x300")

    prompt_label = tk.Label(login_window, text="Welcome to Spotify Insights!\nClick below to sign in with Spotify.\n You will need to grant permissions to the app.")
    prompt_label.pack(pady=10)

    def handle_sign_in():
        try:
            # 1. Connect to Spotify
            sp = connect_to_spotify()
            user = sp.current_user()

            # 2. Close the login window
            login_window.destroy()

            # 3. Open the main UI, etc.
            create_main_window(sp, user["display_name"])
        except Exception as e:
            prompt_label.config(text=f"Error: {e}")

    sign_in_button = tk.Button(login_window, text="Connect to Spotify", command=handle_sign_in, width=30, font=("Helvetica", 12), bg="#1DB954",
                               fg="white")
    sign_in_button.pack(pady=5)
    disclaimer_label = tk.Label(login_window, text="None of your personal information will be shared.")
    disclaimer_label.pack(pady=10)
    version_label = tk.Label(login_window, text="v0.1\nAutomatically gets your current playing track.")
    version_label.pack(pady=10)
    login_window.mainloop()

# Displays the login screen
show_login_screen()

def create_main_window(sp, username, city):
    """
    Create the main window once signed in
    """

    # Main Window
    root = tk.Tk()
    root.title("Spotify Insights")
    root.geometry("400x600")  # NOT FINAL rework maybe after trending.

    # Greeting with spotify username
    greeting_label = tk.Label(root, text=f"Hey, {username}!", font=("Helvetica", 16))
    greeting_label.pack(pady=10)

    # City acknowledgment
    location_label = tk.Label(root, text=f"How's the weather in {city}?", font=("Helvetica", 12))
    location_label.pack(pady=5)

    # Last played track
    track_info_label = tk.Label(root, text="Loading track info...", font=("Helvetica", 12), wraplength=350,
                                justify="center")
    track_info_label.pack(pady=10)

    # Album cover label
    album_label = tk.Label(root)
    album_label.pack(pady=10)

    # Function to refresh data in the UI
    def refresh_data():
        title, artist, album_cover_url = get_current_track(sp)
        if title:
            track_info_label.config(text=f"You're currently listening to \n{title} by {artist}.")
        else:
            track_info_label.config(text=f"You're not currently listening to anything.")


        # Update album cover
        if album_cover_url:
            response = requests.get(album_cover_url)
            img_data = Image.open(BytesIO(response.content))
            img_data = img_data.resize((300, 300))
            album_cover = ImageTk.PhotoImage(img_data)
            album_label.config(image=album_cover) # type: ignore[arg-type]
            album_label.image = album_cover
        else:
            album_label.config(image="", text="[Empty]")

        root.after(3000, refresh_data)

    # Initial data load
    refresh_data()
    refresh_button = tk.Button(root, text="Refresh", command=refresh_data, font=("Helvetica", 12), bg="#1DB954",
                               fg="white")
    refresh_button.pack(pady=20)

    # Start main event loop
    root.mainloop()


# Splash screen

def show_splash():
    """
    Show a splash screen while connecting to Spotify.
    After successful connection, destroy the splash and open the main window.
    """
    splash = tk.Tk()
    splash.title("Connecting to Spotify")
    splash.geometry("300x150")

    # Center the splash text
    label = ttk.Label(splash, text="Connecting to Spotify...\nPlease wait.", font=("Helvetica", 12))
    label.pack(expand=True, pady=20)

    # Attempt Spotify connection on the next GUI cycle
    def attempt_connection():
        try:
            # Connect to Spotify
            sp = connect_to_spotify()
            user = sp.current_user()
            username = user["display_name"]
            city = get_user_location()

            # If successful, close splash
            splash.destroy()

            # Open the main app window
            create_main_window(sp, username, city)
        except Exception as e:
            label.config(text=f"Error:\n{e}")

    # Schedule the connection attempt shortly after splash appears
    splash.after(200, attempt_connection)

    splash.mainloop()


if __name__ == "__main__":
    show_splash()
import os
import time
import spotipy
import zmq
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load Spotify Credentials

load_dotenv('auth.env')
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# Updated Spotify scope to also allow modifying playlists (user-modify-playlist)
SCOPE = (
    "user-read-recently-played "
    "user-read-currently-playing "
    "user-read-playback-state "
    "playlist-read-private "
    "playlist-modify-public "
    "playlist-modify-private"
)

# Spotify + ZeroMQ Setup

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


def init_pub_socket():
    """
    Initialize a ZeroMQ PUB socket for broadcasting track changes.
    PUB allows this to have multiple microservices work off the same burst of info.
    """
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://localhost:5556")
    print("ZeroMQ publisher bound to tcp://localhost:5556")
    return publisher

def init_playcount_req_socket():
    """
    REQ socket for the playcount microservice at tcp://localhost:5557
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5557")
    print("Connected to playcount microservice at tcp://localhost:5557")
    return socket

def init_bpm_req_socket():
    """
    REQ socket for the BPM microservice at tcp://localhost:5558
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5558")
    print("Connected to BPM microservice at tcp://localhost:5558")
    return socket

# Spotify Utility Functions

def get_current_track_info(sp):
    """
    Returns (track_id, title, artist, album_name) if something is playing, else (None, None, None, None).
    """
    current = sp.current_user_playing_track()
    if current and current.get('item'):
        track = current['item']
        track_id = track['id']
        title = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        album_name = track['album']['name']
        return track_id, title, artists, album_name
    return None, None, None, None


def get_user_playlists(sp):
    """
    Fetches a list of the user's playlists.
    Returns a list of (playlist_id, playlist_name).
    """
    playlists = []
    results = sp.current_user_playlists(limit=50)
    for item in results.get('items', []):
        pid = item['id']
        name = item['name']
        playlists.append((pid, name))
    return playlists


def add_track_to_playlist(sp, track_id, playlist_id):
    """
    Adds a single track to the specified playlist.
    """
    if not track_id or not playlist_id:
        return False
    try:
        sp.playlist_add_items(playlist_id, [track_id])
        return True
    except Exception as e:
        print(f"Error adding track: {e}")
        return False


########################
# CLI Menu / Main Loop
########################

def show_menu():
    """
    Prints a small menu and returns the user's choice.
    """
    print("\n--- MENU ---")
    print("1) Check for Track Changes (and publish them)")
    print("2) Show my Playlists")
    print("3) Add Current Track to a Playlist")
    print("4) Quit")
    choice = input("Enter choice: ")
    return choice.strip()


def cli_main():
    """
    CLI-based main function.
    - Connects to Spotify
    - Publishes track changes over ZeroMQ when requested
    - Allows the user to view playlists or add the current track to a chosen playlist
    """
    print("Welcome to Spotify Insights!")
    print("This app is meant to give info on your listening and let you manage playlists.")
    print("A Spotify login is required. Your personal information will NOT be shared.")
    print("Note: A log file (history.log) will be generated in this program's root folder.")
    print("This log file auto-updates with your current track for your own analysis.")
    print("")
    input("Press Enter to connect to Spotify.")

    print("Connecting to Spotify...")
    sp = connect_to_spotify()

    print("Initializing ZeroMQ publisher...")
    publisher = init_pub_socket()

    print("Initializing ZeroMQ REQ socket for playcount...")
    playcount_req = init_playcount_req_socket()

    print("Initializing ZeroMQ REQ socket for bpm...")
    bpm_req = init_bpm_req_socket()

    # Attempt to get user info
    try:
        user = sp.current_user()
        username = user.get("display_name", "User")
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return

    print(f"Hello, {username}!")
    print("Use the menu below to navigate.\n")

    last_track_id = None

    while True:
        choice = show_menu()

        if choice == "1":

            # Check for track changes, and if there's a new track, publish a JSON message
            track_id, title, artists, album = get_current_track_info(sp)

            if track_id is None:
                print("No track is currently playing.")
                last_track_id = None

            else:

                if track_id != last_track_id:
                    # It's a new track, or we just started playing again
                    print(f"You are now listening to '{title}' by {artists}.")
                    # Publish the info
                    message = {
                        "track_id": track_id,
                        "title": title,
                        "artist": artists,
                        "album": album
                    }
                    publisher.send_json(message)
                    time.sleep(0.1)

                    # Playcount display
                    playcount_id = {"track_id": track_id}
                    playcount_req.send_json(playcount_id)
                    response_str = playcount_req.recv_string()
                    try:
                        count = int(response_str)
                        print(f"You've listened to this track {count} times.")
                    except ValueError:
                        print("Error: invalid response from the playcount microservice.")

                    # Request the BPM
                    bpm_req.send_json({"track_id": track_id})
                    bpm_response = bpm_req.recv_json()
                    if "bpm" in bpm_response:
                        tempo = bpm_response["bpm"]
                        speed = bpm_response["speed"]  # "faster than", "the same as", etc.
                        print(f"This track's tempo is {tempo} BPM, {speed} the previous track.")
                    else:
                        print("Error: invalid response from BPM microservice.")

                    last_track_id = track_id

                    input("Press Enter to go back to the main menu.")

                else:
                    print("Same track as before; no new update.")

        elif choice == "2":

            # Show the user's playlists
            print("Fetching your playlists...")
            print("Please note: Spotify's API does NOT allow access to your built-in Liked Songs.")

            playlists = get_user_playlists(sp)

            if not playlists:
                print("No playlists found.")
            else:
                for idx, (pid, name) in enumerate(playlists, start=1):
                    print(f"{idx}. {name}")

        elif choice == "3":

            # Add current track to a chosen playlist
            track_id, title, artists, album = get_current_track_info(sp)

            if track_id is None:
                print("No track is currently playing, cannot add to playlist.")
            else:
                print(f"Current track: '{title}' by {artists}")

                playlists = get_user_playlists(sp)

                if not playlists:
                    print("No playlists found, cannot add track.")
                else:
                    print("\nSelect a playlist to add this track:")
                    print("Please note: Spotify's API does NOT allow access to your built-in Liked Songs.")

                    for idx, (pid, pname) in enumerate(playlists, start=1):
                        print(f"{idx}. {pname}")
                    try:
                        selection = int(input("Enter playlist number (or press Enter to cancel): "))

                        # User cancels.
                        if not selection:
                            print("Canceled adding track to a playlist.")
                            continue

                        chosen_pid, chosen_name = playlists[selection - 1]
                        success = add_track_to_playlist(sp, track_id, chosen_pid)

                        if success:
                            print(f"Track '{title}' added to playlist '{chosen_name}'.")
                        else:
                            print("Failed to add track to the playlist.")

                    except (ValueError, IndexError):
                        print("Invalid selection.")

        elif choice == "4":

            # Quit
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please select from the menu options.")


if __name__ == "__main__":
    cli_main()

import os
import spotipy
import zmq
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Environment setup
load_dotenv('auth.env')
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPE = "user-top-read"

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

def main():
    """
    Receives count, and gets top artists for the user from 1 to {count}
    """

    sp = connect_to_spotify()
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://localhost:5559")
    print("Top Artists microservice is listening on tcp://localhost:5559")

    while True:

        # Wait for the request
        request = socket.recv_json()
        print(f"Received list count: {request}")
        limit = request.get("limit")
        if not limit or not isinstance(limit, int):
            # Send an error if limit is missing or not an integer
            socket.send_json({"error": "Invalid or missing 'limit' field"})
            continue

        # Enforce 1 to 20
        if limit < 1 or limit > 20:
            socket.send_json({"error": "Limit must be between 1 and 20"})
            continue

        # Fetch the user’s top artists
        try:
            # Just gonna keep time range as long_term
            results = sp.current_user_top_artists(limit=limit, time_range="long_term")
            # Extract the artist names
            names = [item["name"] for item in results.get("items", [])]
            socket.send_json({"artists": names})
            print(f"Sent top {limit} artist(s)")
        except Exception as e:
            socket.send_json({"error": str(e)})

if __name__ == "__main__":
    main()

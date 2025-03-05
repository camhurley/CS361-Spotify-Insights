import zmq
import random

last_bpm = None

# Thank you so much to Matthew Wygal for his work on this

def generate_bpm_from_track_id(track_id):
    """
    Deterministically generate a BPM from 80 to 130,
    seeded by the track_id's hash so it's always consistent
    for the same track ID.
    """
    seed_value = hash(track_id)
    random.seed(seed_value)
    return random.randint(80, 130)

def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://localhost:5558")
    print("BPM microservice listening on tcp://localhost:5558 (REQ/REP)")

    global last_bpm

    while True:
        request = socket.recv_json()
        track_id = request.get("track_id")
        if not track_id:
            # If invalid request
            socket.send_json({"error": "No track_id provided"})
            continue

        print(f"[bpm_service] Received track_id: {track_id}")

        # Generate a deterministic "random" BPM
        current_bpm = generate_bpm_from_track_id(track_id)

        # Compare to previous BPM
        if last_bpm is None:
            speed = "N/A"
        else:
            if current_bpm > last_bpm:
                speed = "faster than"
            elif current_bpm < last_bpm:
                speed = "slower than"
            else:
                speed = "the same as"

        # Build response
        response = {
            "bpm": current_bpm,
            "speed": speed
        }

        # Send response back to the client
        socket.send_json(response)
        print(f"[bpm_service] Sent response: {response}")

        # Update last_bpm
        last_bpm = current_bpm

if __name__ == "__main__":
    main()

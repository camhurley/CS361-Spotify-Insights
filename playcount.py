import zmq
import json

LOG_FILENAME = "history.log"  # Make sure this file has the data you want to count

def main():
    """
    Receives a JSON request: { "track_id": "..." } via REQ,
    scans 'history.log' for how many times that track ID appears,
    and sends back the count as a plain string.
    """

    # ZMQ setup
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://localhost:5557")
    print("Playcount microservice (REP) is listening on tcp://localhost:5557")

    while True:

        # Wait for JSON message from main
        request = socket.recv_json()
        track_id = request.get("track_id")
        print(f"Playcount microservice received track_id: {track_id}")

        if not track_id:
            # Return error string if the track ID isn't provided
            socket.send_string("-1")
            continue

        # Iterate over history.log to find hits of our track ID
        count = 0
        try:
            with open(LOG_FILENAME, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("track_id") == track_id:
                            count += 1
                    except json.JSONDecodeError:
                        pass

        # Handling missing log file
        except FileNotFoundError:
            pass

        # Return the count to the main program.
        socket.send_string(str(count))
        print(f"Playcount microservice sent back count: {count}")

if __name__ == "__main__":
    main()

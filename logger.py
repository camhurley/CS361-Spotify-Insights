import zmq
import json

# Define log file name...
LOG_FILENAME = "history.log"

def main():
    """
    Reads the current track info from the ZMQ message then logs it to a file.
    """
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5556")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    print("Logger microservice subscribed to tcp://localhost:5556")

    while True:

        # Receive published JSON
        message = subscriber.recv_json()
        print(f"Logger received: {message}")

        # Append it to our log file as JSON
        with open(LOG_FILENAME, "a", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")
        print("Logged play successfully.")

if __name__ == "__main__":
    main()

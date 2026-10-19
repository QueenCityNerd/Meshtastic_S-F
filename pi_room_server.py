import time
from pubsub import pub
import meshtastic.serial_interface

LOG_FILE = "/home/malachi/mesh_room_log.txt"
MAX_HISTORY_TO_SEND = 5  # Number of lines to return on request

def on_receive(packet, interface):
    try:
        my_node_id = interface.myInfo.my_node_num

        # Look for incoming direct text messages
        if 'decoded' in packet and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
            if packet.get('to') == my_node_id:
                sender = packet.get('fromId', 'Unknown')
                text = packet['decoded'].get('text', '').strip()
                
                print(f"Received from {sender}: {text}")

                # Command 1: If user sends "history" or "read", send back the running list
                if text.lower() in ["history", "read", "board"]:
                    history_text = get_recent_log()
                    print(f"Sending history back to {sender}...")
                    interface.sendText(history_text, destinationId=sender, wantAck=False)

                # Command 2: Anything else gets appended to the board as a new post
                else:
                    timestamp = time.strftime('%m-%d %H:%M')
                    entry = f"[{timestamp}] {sender}: {text}"
                    
                    with open(LOG_FILE, "a") as f:
                        f.write(entry + "\n")
                    
                    # Acknowledge the drop back to the user
                    interface.sendText("Posted to board.", destinationId=sender, wantAck=False)
                    print(f"Added to board: {entry}")

    except Exception as e:
        print(f"Error handling packet: {e}")

def get_recent_log():
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        if not lines:
            return "Board is currently empty."
        # Grab the last N lines
        recent = lines[-MAX_HISTORY_TO_SEND:]
        return "".join(recent).strip()
    except FileNotFoundError:
        return "No log file found yet. Send a message to start it."

if __name__ == "__main__":
    print("Starting Raspberry Pi Mesh Room Server on /dev/ttyUSB0...")
    interface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyUSB0")
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        interface.close()
        print("Room Server stopped.")

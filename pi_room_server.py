import time
import os
from pubsub import pub
import meshtastic.serial_interface

LOG_FILE = "/home/malachi/mesh_room_log.txt"
MAX_HISTORY_TO_SEND = 5  # Number of lines to return on request
SERIAL_PORT = "/dev/ttyUSB0"

def on_receive(packet, interface):
    try:
        my_node_id = interface.myInfo.my_node_num

        # Look for incoming direct text messages
        if 'decoded' in packet and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
            if packet.get('to') == my_node_id:
                sender = packet.get('fromId', 'Unknown')
                text = packet['decoded'].get('text', '').strip()
                
                print(f"Received from {sender}: {text}")

                # Command 1: If user sends "history", "read", or "board", send back log block
                if text.lower() in ["history", "read", "board"]:
                    print(f"Sending history back to {sender}...")
                    send_recent_log(interface, sender)

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

def send_recent_log(interface, destination_id):
    """Reads the log and sends the last 5 entries as a single multi-line packet."""
    if not os.path.exists(LOG_FILE):
        interface.sendText("Board is currently empty.", destinationId=destination_id, wantAck=False)
        return

    try:
        with open(LOG_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        if not lines:
            interface.sendText("Board is currently empty.", destinationId=destination_id, wantAck=False)
            return

        # Grab the last N lines
        recent = lines[-MAX_HISTORY_TO_SEND:]
        
        # Join them together with newlines into a single block
        history_payload = "\n".join(recent)

        # Safety check to ensure it stays well within the ~228 byte limit
        if len(history_payload) > 220:
            history_payload = history_payload[:217] + "..."

        print(f"Sending history block ({len(recent)} lines) to {destination_id}...")
        interface.sendText(history_payload, destinationId=destination_id, wantAck=False)

    except Exception as e:
        print(f"Error reading log file: {e}")
        interface.sendText("Error retrieving history.", destinationId=destination_id, wantAck=False)

if __name__ == "__main__":
    print(f"Starting Raspberry Pi Mesh Room Server on {SERIAL_PORT}...")
    interface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_PORT)
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        interface.close()
        print("Room Server stopped.")

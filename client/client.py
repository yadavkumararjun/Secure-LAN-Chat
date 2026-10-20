import socket
import threading
import os 

SERVER_IP = "127.0.0.1"
PORT = 5000


def receive_messages(client):
    while True:
        try:
            message = client.recv(1024).decode()

            if not message:
                break

            print(f"\n{message}")
            print("You: ", end="")

        except:
            break


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect((SERVER_IP, PORT))

print("Connected to Secure LAN Chat Server!")

# Receive username request
message = client.recv(1024).decode()
print(message)

# Enter username
username = input("Username: ")
client.send(username.encode())

# Receive welcome message
message = client.recv(1024).decode()
print(message)

# Start receiving messages in background
receive_thread = threading.Thread(
    target=receive_messages,
    args=(client,)
)

receive_thread.daemon = True
receive_thread.start()

# Send messages
while True:
    message = input("You: ")

    if message.lower() == "exit":
        client.send("exit".encode())
        break

    if message.startswith("/sendfile "):

        file_path = message[10:]

        if not os.path.exists(file_path):
            print("File not found.")
            continue

        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)

        header = f"FILE|{filename}|{filesize}"

        client.send(header.encode())

        with open(file_path, "rb") as file:

            while True:

                data = file.read(4096)

                if not data:
                    break

                client.sendall(data)

        print(f"File sent: {filename}")

    else:
        client.send(message.encode())
client.close()
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

clients = {}


def send_message(client, message):
    client.send(message.encode())


def broadcast_message(sender_username, message):
    for username, client in clients.items():

        if username != sender_username:

            try:
                send_message(
                    client,
                    f"Broadcast from {sender_username}: {message}"
                )

            except:
                pass


def receive_file(client, filename, filesize):

    received = 0

    file_path = f"../uploads/{filename}"

    with open(file_path, "wb") as file:

        while received < filesize:

            data = client.recv(
                min(4096, filesize - received)
            )

            if not data:
                break

            file.write(data)

            received += len(data)

    return received


def handle_client(client, address):

    print(f"Client connected: {address}")

    # Ask for username
    client.send(
        "Enter your username: ".encode()
    )

    username = client.recv(1024).decode()

    # Prevent duplicate usernames
    if username in clients:

        client.send(
            "Username already taken. Disconnecting.".encode()
        )

        client.close()

        return

    clients[username] = client

    print(f"{username} joined the chat.")

    # Welcome message
    client.send(
        f"Welcome {username}!\n"
        f"Use /msg username message for private messaging.\n"
        f"Use /broadcast message for group messaging.\n"
        f"Use /sendfile filepath to send a file."
        .encode()
    )

    # Communication loop
    while True:

        try:

            message = client.recv(1024).decode()

            if not message:
                break

            if message.lower() == "exit":
                break

            print(f"{username}: {message}")

            # =========================
            # FILE TRANSFER
            # =========================

            if message.startswith("FILE|"):

                parts = message.split("|", 2)

                filename = parts[1]
                filesize = int(parts[2])

                print(f"Receiving file: {filename}")
                print(f"File size: {filesize} bytes")

                received = receive_file(
                    client,
                    filename,
                    filesize
                )

                print(
                    f"File received: {received} bytes"
                )

                send_message(
                    client,
                    f"File uploaded successfully: {filename}"
                )

            # =========================
            # PRIVATE MESSAGE
            # =========================

            elif message.startswith("/msg "):

                parts = message.split(" ", 2)

                if len(parts) < 3:

                    send_message(
                        client,
                        "Usage: /msg username message"
                    )

                    continue

                target_username = parts[1]
                private_message = parts[2]

                if target_username in clients:

                    target_client = clients[
                        target_username
                    ]

                    send_message(
                        target_client,
                        f"Private message from "
                        f"{username}: {private_message}"
                    )

                    send_message(
                        client,
                        f"Message sent to "
                        f"{target_username}"
                    )

                else:

                    send_message(
                        client,
                        f"User '{target_username}' "
                        f"is not online."
                    )

            # =========================
            # BROADCAST MESSAGE
            # =========================

            elif message.startswith("/broadcast "):

                broadcast_message(
                    username,
                    message[11:]
                )

                send_message(
                    client,
                    "Broadcast sent to all connected users."
                )

            # =========================
            # INVALID COMMAND
            # =========================

            else:

                send_message(
                    client,
                    "Invalid command. Use /msg or /broadcast."
                )

        except Exception as e:

            print(
                f"Error with {username}: {e}"
            )

            break

    # Remove client when disconnected
    if username in clients:

        del clients[username]

    client.close()

    print(f"{username} disconnected.")


# =========================
# START SERVER
# =========================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.bind((HOST, PORT))

server.listen(5)

print(f"Server started on port {PORT}")
print("Waiting for clients...")


while True:

    client, address = server.accept()

    thread = threading.Thread(
        target=handle_client,
        args=(client, address)
    )

    thread.start()
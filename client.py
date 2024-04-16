import socket
import json

def main():
    HOST = '127.0.0.1'
    PORT = 49152  # Ensure this matches the server's TCP port

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    username = input("Enter your username: ")
    client.sendall(username.encode('utf-8'))  # Send username for initial connection

    print("Connected to the server. Type 'exit' to quit, 'chat' to send a message, or a number (1-9) to make a move.")

    while True:
        try:
            server_response = client.recv(1024).decode('utf-8')
            if not server_response:
                print("No response from server, closing connection.")
                break
            
            try:
                message = json.loads(server_response)
                if 'message' in message:
                    print(f"Server says: {message['message']}")
                if 'board' in message:
                    print("Current board state:", message['board'])
            except json.JSONDecodeError:
                print("Server message:", server_response)

            user_input = input("Enter your move (1-9), 'chat' to send a message, or 'exit' to quit: ")
            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'chat':
                chat_message = input("Enter your message: ")
                client.sendall(json.dumps({"action": "chat", "message": chat_message}).encode('utf-8'))
            else:
                client.sendall(json.dumps({"action": "move", "move": user_input}).encode('utf-8'))

        except Exception as e:
            print(f"An error occurred: {e}")
            break

    client.close()
    print("Disconnected from the server.")

if __name__ == '__main__':
    main()

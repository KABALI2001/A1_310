import asyncio
import websockets
import socket
import threading
import json
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

# Game board representation
board = [" " for _ in range(9)]

# A dictionary to keep track of users and their corresponding WebSocket.
connected_users = {}

# Winning combinations
win_combinations = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Horizontal
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Vertical
    (0, 4, 8), (2, 4, 6)              # Diagonal
]

def check_winner():
    for combo in win_combinations:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != " ":
            return board[combo[0]]  # Return 'X' or 'O'
    if " " not in board:
        return "Draw"
    return None

def reset_board():
    global board
    board = [" " for _ in range(9)]

async def broadcast_message(message):
    for ws in connected_users.values():
        await ws.send(message)

def make_server_move():
    empty_indices = [i for i, x in enumerate(board) if x == " "]
    if not empty_indices:
        return None
    move = random.choice(empty_indices)
    board[move] = 'O'
    return move

class GameHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        if data['action'] == 'move':
            index = int(data['move'])
            if 0 <= index < 9 and board[index] == " ":
                board[index] = 'X'  # Player's move
                make_server_move()
                winner = check_winner()
                if winner:
                    response = {'board': board, 'winner': winner}
                    reset_board()
                else:
                    response = {'board': board, 'winner': "No winner yet"}
            else:
                response = {'error': 'Position already taken', 'board': board}
        elif data['action'] == 'reset':
            reset_board()
            response = {'board': board, 'winner': "No winner"}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, GameHTTPRequestHandler)
    print("HTTP Server running on port 8000")
    httpd.serve_forever()

def handle_tcp_client(conn, addr):
    print(f"TCP Connection from {addr}")
    while True:
        data = conn.recv(1024).decode('utf-8').strip()
        if not data:
            break
        print(f"Received from TCP client {addr}: {data}")
        conn.sendall(data.encode('utf-8'))
    conn.close()
    print(f"TCP connection with {addr} closed")

def start_tcp_server():
    HOST = '127.0.0.1'
    PORT = 49152
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"TCP Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_tcp_client, args=(conn, addr)).start()

async def websocket_handler(websocket, path):
    username = ''
    try:
        auth_data = await websocket.recv()
        user_info = json.loads(auth_data)
        username = user_info.get("username")
        if not username:
            await websocket.close(reason="Authentication failed: Username not provided.")
            return
        connected_users[username] = websocket
        await broadcast_message(json.dumps({"type": "info", "message": f"{username} has joined the game."}))
        await websocket.send(json.dumps({"type": "board", "board": board}))

        async for message in websocket:
            data = json.loads(message)
            if data.get("action") == "chat":
                await broadcast_message(json.dumps({"type": "chat", "message": f"{username}: {data['message']}"}))
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
    finally:
        if username in connected_users:
            del connected_users[username]
            await broadcast_message(json.dumps({"type": "info", "message": f"{username} has left the game."}))

async def start_websocket_server():
    async with websockets.serve(websocket_handler, "localhost", 49153):
        print("WebSocket Server running on ws://localhost:49153/")
        await asyncio.Future()  # Run forever

def main():
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, start_tcp_server)
    loop.run_in_executor(None, run_http_server)
    loop.run_forever()

if __name__ == "__main__":
    main()

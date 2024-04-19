import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

class TicTacToeGame:
    def __init__(self, player1, player2):
        self.players = {player1: 'X', player2: 'O'}
        self.player_names = {player1: '', player2: ''}
        self.board = [' ' for _ in range(9)]
        self.current_player = player1

    def register_name(self, player, name):
        self.player_names[player] = name

    def make_move(self, player, position):
        if player == self.current_player and self.board[position] == ' ':
            self.board[position] = self.players[player]
            self.current_player = next(p for p in self.players if p != player)  # Toggle current player
            return True
        return False

    def check_winner(self):
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for line in lines:
            if self.board[line[0]] == self.board[line[1]] == self.board[line[2]] != ' ':
                return self.board[line[0]]
        if ' ' not in self.board:
            return 'Draw'
        return None

    def reset_board(self):
        self.board = [' ' for _ in range(9)]

clients = {}
games = {}
waiting_player = None

async def handler(websocket, path):
    global waiting_player
    try:
        name_data = await websocket.recv()
        name = json.loads(name_data)['name']
        clients[websocket] = name
        logging.info(f"{name} connected.")

        if waiting_player and waiting_player.open:
            # Start a new game
            game = TicTacToeGame(waiting_player, websocket)
            games[waiting_player] = games[websocket] = game
            game.register_name(waiting_player, clients[waiting_player])
            game.register_name(websocket, clients[websocket])
            await notify_players(game, {"action": "start"})
            waiting_player = None
        else:
            waiting_player = websocket
            await websocket.send(json.dumps({"action": "wait"}))

        while True:
            message = await websocket.recv()
            data = json.loads(message)
            game = games.get(websocket)

            if data['action'] == 'move':
                if game.make_move(websocket, int(data['position'])):
                    winner = game.check_winner()
                    if winner:
                        await notify_players(game, {"action": "winner", "winner": winner})
                        game.reset_board()
                    else:
                        await notify_players(game, {"action": "move", "board": game.board})
            elif data['action'] == 'reset':
                game.reset_board()
                await notify_players(game, {"action": "reset", "board": game.board})
            elif data['action'] == 'chat':
                await notify_players(game, {"action": "chat", "name": clients[websocket], "message": data['message']})

    except websockets.exceptions.ConnectionClosed:
        if websocket in games:
            game = games[websocket]
            opponent = next((p for p in game.players if p != websocket), None)
            if opponent:
                await opponent.send(json.dumps({"action": "opponent_left"}))
            games.pop(websocket, None)
            clients.pop(websocket, None)
        if websocket == waiting_player:
            waiting_player = None
        logging.info(f"{name} disconnected.")

async def notify_players(game, message):
    msg = json.dumps(message)
    for player in game.players:
        if player.open:  # Ensure the WebSocket connection is open before sending
            await player.send(msg)

start_server = websockets.serve(handler, "localhost", 6789)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

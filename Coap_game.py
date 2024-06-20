import tkinter as tk
import random
import asyncio
import logging
import threading
from aiocoap import *

class Game:
    def __init__(self, root, loop):
        self.root = root
        self.loop = loop
        self.root.title("Spiel")
        self.canvas = tk.Canvas(root, width=300, height=400)
        self.canvas.pack()
        self.player_position = 1  # Startposition des Spielers (mittlere Bahn)
        self.speed = 5  # Standard-Geschwindigkeit des rollenden Punktes
        self.rounds = 0  # Anzahl der Runden
        self.level = 1  # Aktuelles Level
        self.balls = []  # Liste der rollenden Bälle
        self.create_lanes()
        self.create_player()
        self.create_rolling_point()
        self.root.bind("<Left>", self.move_left)
        self.root.bind("<Right>", self.move_right)
        self.running = True
        self.update_rolling_point()

    def create_lanes(self):
        self.canvas.create_line(100, 0, 100, 400, fill="black")
        self.canvas.create_line(200, 0, 200, 400, fill="black")

    def create_player(self):
        self.player = self.canvas.create_oval(145, 370, 155, 380, fill="blue")

    def create_rolling_point(self):
        self.balls.append(self.create_ball())

    def create_ball(self, lane=None):
        if lane is None:
            available_lanes = [0, 1, 2]
            for _, ball_lane in self.balls:
                if ball_lane in available_lanes:
                    available_lanes.remove(ball_lane)
            lane = random.choice(available_lanes)
        ball = self.canvas.create_oval(45 + lane * 100, 0, 55 + lane * 100, 10, fill="red")
        return ball, lane

    def update_rolling_point(self):
        if not self.running:
            return
        for i, (ball, lane) in enumerate(self.balls):
            self.canvas.move(ball, 0, self.speed)
            pos = self.canvas.coords(ball)
            if pos[1] >= 400:
                available_lanes = [0, 1, 2]
                for _, ball_lane in self.balls:
                    if ball_lane in available_lanes:
                        available_lanes.remove(ball_lane)
                new_lane = random.choice(available_lanes)
                self.canvas.coords(ball, 45 + new_lane * 100, 0, 55 + new_lane * 100, 10)
                self.balls[i] = (ball, new_lane)
                self.rounds += 1
                if (self.level < 4 and self.rounds % 5 == 0) or (self.level >= 4 and self.rounds % 10 == 0):
                    self.level_up()
        self.check_collision()
        self.root.after(50, self.update_rolling_point)  # Schnellere Bewegung durch kürzeres Intervall

    def move_left(self, event=None):
        if self.player_position > 0:
            self.player_position -= 1
            self.canvas.move(self.player, -100, 0)

    def move_right(self, event=None):
        if self.player_position < 2:
            self.player_position += 1
            self.canvas.move(self.player, 100, 0)

    def check_collision(self):
        player_pos = self.canvas.coords(self.player)
        for ball, _ in self.balls:
            rolling_pos = self.canvas.coords(ball)
            if player_pos[0] < rolling_pos[2] and player_pos[2] > rolling_pos[0] and player_pos[1] < rolling_pos[3] and player_pos[3] > rolling_pos[1]:
                print("Kollision!")
                self.running = False
                self.root.after(100, self.root.destroy)  # Spiel beenden nach Kollision

    def level_up(self):
        self.level += 1
        if self.level < 4:
            self.speed += 2
        elif self.level >= 5:
            self.speed += 2  # Geschwindigkeit ab Level 5 wieder erhöhen
        if self.level >= 4 and len(self.balls) == 1:
            self.balls.append(self.create_ball())
        self.show_level_message()

    def show_level_message(self):
        level_label = tk.Label(self.root, text=f"Level {self.level}", font=("Helvetica", 32), fg="white", bg="black")
        level_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.root.after(2000, level_label.destroy)  # Entferne die Level-Meldung nach 2 Sekunden

    def set_speed(self, speed):
        self.speed = speed

class CoAPClient:
    def __init__(self, game):
        self.game = game
        self.payload_value = None  # Variable zur Speicherung des Payload-Werts

    async def run_client(self, ip, port, resource):
        protocol = await Context.create_client_context()
        uri = f'coap://{ip}:{port}/{resource}'
        request = Message(code=GET, uri=uri)
        try:
            response = await protocol.request(request).response
            logging.info(f"Response from {uri}: {response}")
            self.process_payload(response.payload)
        except Exception as e:
            logging.error(f"Failed to get resource: {e}")

    def process_payload(self, payload):
        try:
            number = int(payload.decode('utf-8'))
            self.payload_value = number  # Speichern des Payload-Werts
            self.game.set_speed(5)  # Setze die Geschwindigkeit auf einen Standardwert
            # Bedingungen für die Bewegung
            if number > 2400:
                self.game.move_right()
            elif number < 1700:
                self.game.move_left()
        except ValueError:
            logging.error("Failed to decode payload as integer")

    async def periodic_request(self, ip, port, resource, interval=1):
        while True:
            await self.run_client(ip, port, resource)
            await asyncio.sleep(interval)

def start_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def main():
    root = tk.Tk()
    loop = asyncio.new_event_loop()
    game = Game(root, loop)

    # CoAP client configuration
    coap_client = CoAPClient(game)
    ip = "169.254.14.138"  # Beispiel-IP, bitte anpassen
    port = 5683  # Beispiel-Port, bitte anpassen
    resource = "zahl"  # Beispiel-Ressource, bitte anpassen

    # Create a new asyncio loop and run it in a separate thread
    t = threading.Thread(target=start_async_loop, args=(loop,))
    t.start()

    # Start periodic CoAP requests in the new loop
    asyncio.run_coroutine_threadsafe(coap_client.periodic_request(ip, port, resource, interval=1), loop)

    # Start Tkinter main loop
    root.mainloop()
    loop.call_soon_threadsafe(loop.stop)

if __name__ == "__main__":
    main()

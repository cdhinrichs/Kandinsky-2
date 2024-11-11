import discord
import os, re, io
import asyncio

from multiprocessing import Queue
from multiprocessing.managers import BaseManager
from threading import Thread

API_key = os.getenv("DBOT_API_KEY")
if API_key is None:
  print('API key must be supplied in env variable "DBOT_API_KEY"')
  exit(0)
PORT = os.getenv("DBOT_PORT", 9000)

msg_q = Queue() # A Queue for sending prompts
img_q = Queue() # A Queue for sending images

class QManager(BaseManager): pass
QManager.register("msg_q", callable=lambda: msg_q)
QManager.register("img_q", callable=lambda: img_q)

manager = QManager(address=("localhost", int(PORT)), authkey=API_key.encode("utf8"))
server = manager.get_server()
server_p = Thread(target=server.serve_forever)
server_p.start()
print("Qmanager started")


class DBOTClient(discord.Client):
  def __init__(self):
    self.messages = {}
    self.msg_q = msg_q

    intents = discord.Intents.default()
    super(DBOTClient, self).__init__(intents=intents)

  async def on_ready(self):
    print(f'We have logged in as {self.user}')

  async def on_message(self, message):
    if message.author == self.user:
      return

    if not message.content:
      return # None of my business, apparently

    prompt = re.sub("<@[0-9]+> ", "", message.content)

    # Save the message for later.
    self.msg_q.put([message.id, prompt])
    self.messages[message.id] = message
    await message.channel.send(content=f"Your prompt '{prompt}' is in the queue")

def DBOT_send_reply(client, key, image):
  message = client.messages[key]
  prompt = re.sub("<@[0-9]+> ", "", message.content)

  buff = io.BytesIO()
  image.save(buff, format="png")
  buff.seek(0)
  image_file = discord.File(buff, "image.png", description=prompt)

  asyncio.run_coroutine_threadsafe(
    message.channel.send(
      content=f"Here is your image for \n'{prompt}'",
      reference=message.to_reference(),
      file=image_file
    ),
    client.loop)



client = DBOTClient()
def serve(client):
  while True:
    key, image = img_q.get()
    DBOT_send_reply(client, key, image)
    del client.messages[key]

# p = Thread(target=client.run, args=(API_key,))
p = Thread(target=serve, args=(client,))
p.start()

client.run(API_key)



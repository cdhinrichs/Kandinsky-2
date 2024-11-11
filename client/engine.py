import os

from kandinsky2 import get_kandinsky2
from PIL import Image
from multiprocessing.managers import BaseManager

PORT = int(os.getenv("DBOT_PORT", 9000))
API_key = os.getenv("DBOT_API_KEY")
if API_key is None:
  print('API key must be supplied in env variable "DBOT_API_KEY"')
  exit(0)


txt2img_model = get_kandinsky2('cuda', task_type='text2img',
    model_version='2.1', use_flash_attention=False)

txt2images = lambda prompt, size=768: txt2img_model.generate_text2img(
    prompt,
    num_steps=100,
    batch_size=1,
    guidance_scale=4,
    h=size, w=size,
    sampler='p_sampler',
    prior_cf_scale=4,
    prior_steps="5"
)[0]


class QManager(BaseManager): pass
QManager.register("msg_q")
QManager.register("img_q")
manager = QManager(address=("localhost", int(PORT)), authkey=API_key.encode("utf8"))
manager.connect()
msg_q = manager.msg_q()
img_q = manager.img_q()

print("Ready!")

while True:
  key, prompt = msg_q.get()
  print(prompt)
  image = txt2images(prompt, 768)
  img_q.put((key, image))

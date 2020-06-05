# HEOS

Use python to control your HEOS system.

Here as example on how to use it:
[![asciicast](https://asciinema.org/a/336820.png)](https://asciinema.org/a/336820)

After installing use:
```python
import heos
h=HEOS(ip=ip_of_your_system)

print(h) # shows current status

h.volume.get()   # asks current volume
h.volume.set(20) # change volume to 20

h.favorites.show()  # show presets
h.favorites.play(2) # start playing favorite saved in n.2

h.play.playing() # shows what is currently being played
h.play.next()
h.play.cd()
```
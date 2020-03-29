# TuSanic

![GitHub stars](https://img.shields.io/github/stars/avi-av/TuSanic?style=social)

---

**TuSanic** is a tus.io server-side implementation for [sanic](https://sanicframework.org/)

tus is _resumable uploads_ protocol.
visit tus.io for more information

The project code is based on the code written by [@matthoskins1980](https://github.com/matthoskins1980/Flask-Tus)

## Installation

- `pip3 install TuSanic`
  or
- `git clone https://github.com/avi-av/TuSanic && cd TuSanic`
- `python3 setup.py install`

## Usage

```python
from sanic import Sanic
from TuSanic import Tus

app = Sanic('tusanic_demo')
tus = Tus(app)

@tus.upload_file_handler
def file_upload(path, filename):
    print(f"save {filename} to {path}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

#### clients for tus.io protocol

- python (&cli) [github.com/cenkalti/tus.py](https://github.com/cenkalti/tus.py)
- JS (Browser) [uppy.io](https://uppy.io/docs/tus/)

#### License

`MIT`

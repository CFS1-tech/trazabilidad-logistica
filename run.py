from app.main import app
from config.settings import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

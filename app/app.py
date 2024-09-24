# app.py
from flask import Flask
from src.routes.main_routes import main_bp


app = Flask(__name__)

# Registrar los Blueprints
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True)
from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance imported by all models and app factory
db = SQLAlchemy()

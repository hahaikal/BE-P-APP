from .database import engine, Base
from . import model  # Import models to register them with Base metadata

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()

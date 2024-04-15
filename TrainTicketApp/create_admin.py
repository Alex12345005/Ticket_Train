# create_admin.py
from app import db, app  # Stellt sicher, dass die App und DB aus deinem Flask-Projekt importiert werden
from models import User

def create_admin(username, password):
    """ Erstellt einen neuen Admin-Benutzer in der Datenbank. """
    with app.app_context():  # Verwendet den Anwendungskontext, um auf die DB zuzugreifen
        if User.query.filter_by(username=username).first():
            print("Ein Benutzer mit diesem Namen existiert bereits.")
        else:
            new_admin = User(username=username, password=password, is_admin=True)
            db.session.add(new_admin)
            db.session.commit()
            print(f"Admin {username} wurde erfolgreich angelegt.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <username> <password>")
    else:
        username = sys.argv[1]
        password = sys.argv[2]
        create_admin(username, password)

# test_routes.py
import pytest

from ..app import app, db
from ..models import Buchung
from datetime import datetime

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_index_get(client):
    """ Testet die GET-Anfrage für die Startseite. """
    response = client.get('/')
    assert response.status_code == 200
    assert 'Willkommen' in response.get_data(as_text=True)

def test_index_post(client):
    """ Testet die POST-Anfrage für die Startseite mit einer neuen Buchung. """
    response = client.post('/', data={
        'name': 'John Doe',
        'zugnummer': '123',
        'abfahrtsort': 'Graz Hauptbahnhof',
        'zielort': 'Bruck an der Mur',
        'abfahrtszeit': '2024-01-01T12:00'
    })
    assert response.status_code == 302
    assert '/buchung-best%C3%A4tigt' in response.headers['Location']

def test_stornierung(client):
    with client.application.app_context():  # Stelle sicher, dass der Code im App-Kontext ausgeführt wird
        abfahrtszeit = datetime.strptime("2024-05-05T12:00", "%Y-%m-%dT%H:%M")
        buchung = Buchung(
            name="Test User",
            zugnummer="1234",
            abfahrtsort="Graz",
            zielort="Wien",
            abfahrtszeit=abfahrtszeit,
            preis=100,
            storniert=False,
            reiseklasse="Economy"
        )
        db.session.add(buchung)
        db.session.commit()
        
        response = client.get(f'/stornieren/{buchung.id}')
        assert response.status_code == 302
        
        updated_buchung = Buchung.query.get(buchung.id)
        assert updated_buchung.storniert == True
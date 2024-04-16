# test_routes.py
import pytest
from unittest.mock import patch
from ..app import app, db
from ..models import Buchung, User
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
    """Test the GET request for the home page when user is logged in."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    response = client.get('/')
    assert response.status_code == 200
    assert 'Willkommen' in response.get_data(as_text=True)

def test_stornierung(client):
    """Test booking cancellation."""
    with client.application.app_context():
        user = User(username='testuser', password='testpass')
        db.session.add(user)
        db.session.commit()

        abfahrtszeit = datetime.strptime("2024-05-05T12:00", "%Y-%m-%dT%H:%M")
        buchung = Buchung(
            user_id=user.id,  # Assign the user's ID
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

        updated_buchung = db.session.query(Buchung).get(buchung.id)
        assert updated_buchung.storniert == True

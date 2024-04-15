import pytest
from ..app import calculate_distance, create_pdf, generate_train_number, generate_random_abfahrtszeiten
from ..models import db, Buchung
from datetime import datetime

import os

@pytest.mark.parametrize("lat1, lon1, lat2, lon2, expected", [
    (47.0667, 15.4333, 47.4105, 15.2772, 40.00),  # Graz zu Bruck an der Mur
    (47.4105, 15.2772, 47.3820, 15.0946, 14.11),  # Bruck an der Mur zu Leoben
])
def test_calculate_distance(lat1, lon1, lat2, lon2, expected):
    tolerance = 0.5  # Toleranz in km
    result = calculate_distance(lat1, lon1, lat2, lon2)
    assert abs(result - expected) <= tolerance, f"Expected {expected}, but got {result}"

def test_create_pdf():
    """Testet die Erstellung einer PDF-Datei."""
    abfahrtszeit = datetime.strptime("2024-05-05T12:00", "%Y-%m-%dT%H:%M")
    buchung = Buchung(name="Test User", zugnummer="1234", abfahrtsort="Graz", zielort="Wien", 
                      abfahrtszeit=abfahrtszeit, preis=100, reiseklasse="First")
    pdf_path = create_pdf(buchung)
    assert os.path.exists(pdf_path)
    os.remove(pdf_path)

def test_generate_train_number():
    """ Testet, ob die generierte Zugnummer das korrekte Format hat. """
    train_number = generate_train_number()
    assert len(train_number) == 5, "Die Zugnummer sollte genau 5 Zeichen lang sein"
    assert train_number[:2].isalpha() and train_number[2:].isdigit(), "Die Zugnummer sollte mit 2 Buchstaben beginnen und mit 3 Ziffern enden"

def test_generate_random_abfahrtszeiten():
    """ Testet, ob korrekte Abfahrtszeiten generiert werden. """
    abfahrtszeiten = generate_random_abfahrtszeiten()
    assert len(abfahrtszeiten) == 7, "Sollte Abfahrtszeiten für 7 Tage generieren"
    for day in abfahrtszeiten:
        day_name, times = day
        assert len(times) >= 1, f"Jeder Tag sollte mindestens eine Abfahrtszeit haben ({day_name})"

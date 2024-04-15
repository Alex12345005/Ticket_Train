from datetime import datetime, timedelta
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from models import User, db, Buchung
from flask import flash
from sqlalchemy.exc import IntegrityError
from reportlab.pdfgen import canvas
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4

import os
import base64
import tempfile
import random
import string

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Test123')

def jinja2_filter_enumerate(sequence):
    return enumerate(sequence)

app.jinja_env.filters['enumerate'] = jinja2_filter_enumerate

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zugreisen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

station_coordinates = {
    "Graz Hauptbahnhof": (47.0667, 15.4333),
    "Bruck an der Mur": (47.4105, 15.2772),
    "Leoben Hauptbahnhof": (47.3820, 15.0946),
    "Kapfenberg": (47.4425, 15.2860),
    "Frohnleiten": (47.2739, 15.3194),
    "Knittelfeld": (47.2153, 14.8227),
    "Mürzzuschlag": (47.6039, 15.6728),
    "Leibnitz": (46.7812, 15.5452),
    "Fehring": (46.9311, 15.8950),
    "Spielfeld-Straß": (46.7184, 15.6484),
    "Weiz": (47.2167, 15.6167)
}

def calculate_distance(lat1, lon1, lat2, lon2):
    from math import radians, cos, sin, sqrt, atan2

    R = 6371.0  

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    distance = R * c
    return distance

def generate_train_number():
    numbers = ''.join(random.choices(string.digits, k=3))
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    return f"{letters}{numbers}"

def generate_random_abfahrtszeiten(start_hour=6, end_hour=22, interval_minutes=60, num_days=7):
    """Generates human-readable and datetime values for departure times over multiple days."""
    base_date = datetime.now()
    abfahrtszeiten = []
    for day in range(num_days):
        date = base_date + timedelta(days=day)
        day_times = []
        hour = start_hour
        while hour < end_hour:
            minute_offset = random.randint(0, interval_minutes - 1)
            time = datetime(date.year, date.month, date.day, hour, minute_offset)
            formatted_time = time.strftime('%A, %d. %B %Y, %H:%M Uhr')  # Human-readable format
            day_times.append((formatted_time, time))  # Tuple of formatted and datetime values
            hour += 1
        abfahrtszeiten.append((date.strftime('%A'), day_times))  # Save as tuple (day_name, list_of_times)
    return abfahrtszeiten

def send_email_with_attachment(to_emails, subject, content, attachment_path):
    message = Mail(
        from_email='wadu0185@gmail.com',
        to_emails=to_emails,
        subject=subject,
        html_content=content
    )

    with open(attachment_path, 'rb') as f:
        data = f.read()
    encoded_file = base64.b64encode(data).decode()

    attachedFile = Attachment(
        FileContent(encoded_file),
        FileName('Rechnung.pdf'),
        FileType('application/pdf'),
        Disposition('attachment')
    )
    message.attachment = attachedFile

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code, response.body, response.headers)
    except Exception as e:
        print(e.message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('index'))
        else:
            flash('Falscher Benutzername oder Passwort', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Prüfe, ob der Benutzername schon existiert
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben', 'error')
            return redirect(url_for('register'))
        # Erstelle neuen Benutzer
        new_user = User(username=username, password=password)  # Sicherheitshinweis: Passwörter sollten gehasht gespeichert werden
        db.session.add(new_user)
        db.session.commit()
        flash('Registrierung erfolgreich. Bitte loggen Sie sich ein.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    preis = None
    abfahrtsort = None
    zielort = None
    abfahrtszeit = generate_random_abfahrtszeiten()
    
    if request.method == 'POST':
        name = request.form.get('name')
        zugnummer = generate_train_number()
        abfahrtsort = request.form.get('abfahrtsort')
        zielort = request.form.get('zielort')
        abfahrtszeit_index = request.form.get('abfahrtszeit_index')

        # Überprüfen Sie, ob ein Index ausgewählt wurde
        if abfahrtszeit_index is not None:
            selected_index = int(abfahrtszeit_index)
            abfahrtszeit_selected = abfahrtszeit[0][1][selected_index][1]  # Access the datetime object from the tuple
        else:
            # Fehlerbehandlung oder Standardwert setzen
            flash('Bitte wählen Sie eine Abfahrtszeit aus.', 'error')
            return redirect(url_for('index'))

        abfahrtsort_coords = station_coordinates.get(abfahrtsort)
        zielort_coords = station_coordinates.get(zielort)

        if abfahrtsort_coords and zielort_coords:
            distanz = calculate_distance(*abfahrtsort_coords, *zielort_coords)
            preis = distanz * 0.30
            preis = round(preis, 2)

        reiseklasse = request.form.get('reiseklasse')
        if reiseklasse == "Business":
            preis *= 1.5
        elif reiseklasse == "First":
            preis *= 2.0

        neue_buchung = Buchung(user_id=session['user_id'], name=name, zugnummer=zugnummer, abfahrtsort=abfahrtsort, zielort=zielort, abfahrtszeit=abfahrtszeit_selected, preis=preis, reiseklasse=reiseklasse)
        db.session.add(neue_buchung)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Ein Fehler ist aufgetreten. Die Buchung konnte nicht gespeichert werden.', 'error')
            return redirect(url_for('index'))

        return redirect(url_for('buchung_bestätigt', buchungs_id=neue_buchung.id))
    else:
        # Hier prüfen wir, ob der Benutzer ein Admin ist und laden entsprechend die Buchungen
        if session.get('is_admin'):
            buchungen = Buchung.query.filter_by(storniert=False).all()
        else:
            buchungen = Buchung.query.filter_by(user_id=session['user_id'], storniert=False).all()
        return render_template('index.html', buchungen=buchungen, abfahrtszeit=abfahrtszeit, preis=preis)

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/stornieren/<int:buchungs_id>')
def stornieren(buchungs_id):
    print("Storniere Buchung mit ID:", buchungs_id)  # Debugging-Ausgabe hinzufügen
    buchung = Buchung.query.get_or_404(buchungs_id)
    print("Gefundene Buchung:", buchung)  # Debugging-Ausgabe hinzufügen
    buchung.storniert = True
    db.session.commit()
    print("Buchung erfolgreich storniert")  # Debugging-Ausgabe hinzufügen
    return redirect(url_for('index') + '?showBuchungen=true')


@app.route('/rechnung/<int:buchungs_id>')
def rechnung(buchungs_id):
    buchung = Buchung.query.get_or_404(buchungs_id)
    pdf_path = create_pdf(buchung)
    response = send_file(pdf_path, as_attachment=True)
    return response

@app.route('/buchung-bestätigt/<int:buchungs_id>')
def buchung_bestätigt(buchungs_id):
    return render_template('booking_confirmation.html', buchungs_id=buchungs_id)

def create_pdf(buchung):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    filepath = temp_file.name
    c = canvas.Canvas(filepath, pagesize=A4)

    # Kopfzeile und Titel der Rechnung
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(105 * mm, 280 * mm, "Rechnung für Ihre Buchung")
    c.line(15 * mm, 265 * mm, 195 * mm, 265 * mm)

    # Details der Buchung auflisten
    details_y_start = 260 * mm
    details = [
        ("Name:", buchung.name),
        ("Reiseklasse:", buchung.reiseklasse),
        ("Zugnummer:", buchung.zugnummer),
        ("Abfahrtsort:", buchung.abfahrtsort),
        ("Zielort:", buchung.zielort),
        ("Abfahrtszeit:", buchung.abfahrtszeit.strftime('%A, %d. %B %Y, %H:%M Uhr')),
        ("Preis:", f"{buchung.preis:.2f} Euro")
    ]
    for label, value in details:
        c.setFont("Helvetica-Bold", 12)  # Setzt die Schriftart für das Label auf fett
        c.drawString(15 * mm, details_y_start, label)
        c.setFont("Helvetica", 12)  # Setzt die Schriftart für den Wert zurück auf normal
        c.drawString(45 * mm, details_y_start, value)
        details_y_start -= 10 * mm

    # Logo einfügen
    image_path = os.path.join(os.path.dirname(__file__), 'pics', 'öbblogo.png')
    image_width = 150 * mm
    image_height = 150 * mm
    image_x = (A4[0] - image_width) / 2
    image_y = details_y_start - 155 * mm
    c.drawImage(image_path, image_x, image_y, width=image_width, height=image_height, preserveAspectRatio=True)

    c.showPage()
    c.save()
    temp_file.close()
    return filepath

@app.route('/send-email/<int:buchungs_id>', methods=['POST'])
def send_email(buchungs_id):
    buchung = Buchung.query.get_or_404(buchungs_id)
    pdf_path = create_pdf(buchung)

    user_email = request.form['email']

    send_email_with_attachment(
        to_emails=user_email,
        subject="Ihre Rechnung für die Buchung bei Zugreisen",
        content="Vielen Dank für Ihre Buchung. Im Anhang finden Sie Ihre Rechnung.",
        attachment_path=pdf_path
    )

    return redirect(url_for('buchung_bestätigt', buchungs_id=buchungs_id, message='Rechnung erfolgreich gesendet'))

if __name__ == '__main__':
    app.run(debug=True)
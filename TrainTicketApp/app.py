from datetime import datetime
from flask import Flask, redirect, render_template, request, send_file, url_for
from models import db, Buchung
from flask import flash
from sqlalchemy.exc import IntegrityError
from reportlab.pdfgen import canvas
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv

import os
import base64
import tempfile

load_dotenv()

app = Flask(__name__)
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

@app.route('/', methods=['GET', 'POST'])
def index():
    preis = None  
    abfahrtsort = None  
    zielort = None  

    if request.method == 'POST':
        name = request.form.get('name')
        zugnummer = request.form.get('zugnummer')
        abfahrtsort = request.form.get('abfahrtsort')
        zielort = request.form.get('zielort')
        abfahrtszeit = datetime.strptime(request.form.get('abfahrtszeit'), '%Y-%m-%dT%H:%M')
        abfahrtsort_coords = station_coordinates.get(abfahrtsort)
        zielort_coords = station_coordinates.get(zielort)

        if abfahrtsort_coords and zielort_coords:
            distanz = calculate_distance(*abfahrtsort_coords, *zielort_coords)
            preis = distanz * 0.30 
            preis = round(preis, 2)

        neue_buchung = Buchung(name=name, zugnummer=zugnummer, abfahrtsort=abfahrtsort, zielort=zielort, abfahrtszeit=abfahrtszeit, preis=preis)
        db.session.add(neue_buchung)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return "Ein Fehler ist aufgetreten. Die Buchung konnte nicht gespeichert werden.", 400

        return redirect(url_for('buchung_bestätigt', buchungs_id=neue_buchung.id))

    else:
        abfahrtsort = request.args.get('abfahrtsort')
        zielort = request.args.get('zielort')
        preis = None  

        abfahrtsort_coords = None
        zielort_coords = None

        if abfahrtsort and zielort:
            abfahrtsort_coords = station_coordinates.get(abfahrtsort)
            zielort_coords = station_coordinates.get(zielort)

            if abfahrtsort_coords and zielort_coords:
                distanz = calculate_distance(*abfahrtsort_coords, *zielort_coords)
                preis = distanz * 0.30  

        buchungen = Buchung.query.all()
        return render_template('index.html', buchungen=buchungen, preis=preis, abfahrtsort=abfahrtsort, zielort=zielort)    
@app.route('/stornieren/<int:buchungs_id>')
def stornieren(buchungs_id):
    buchung = Buchung.query.get_or_404(buchungs_id)
    buchung.storniert = True
    db.session.commit()
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
    c = canvas.Canvas(filepath)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(300, 800, "Rechnung für Ihre Buchung")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Buchungsnummer: {buchung.id}")

    c.line(50, 760, 550, 760)

    details_y_start = 740
    details = [
        f"Name: {buchung.name}",
        f"Zugnummer: {buchung.zugnummer}",
        f"Abfahrtsort: {buchung.abfahrtsort}",
        f"Zielort: {buchung.zielort}",
        f"Abfahrtszeit: {buchung.abfahrtszeit.strftime('%Y-%m-%d %H:%M')}",
        f"Preis: {buchung.preis} Euro"
    ]
    for detail in details:
        c.drawString(50, details_y_start, detail)
        details_y_start -= 20

    c.showPage()
    c.save()

    temp_file.close()
    return filepath

@app.route('/map')
def map_view():
    return render_template('map.html')


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
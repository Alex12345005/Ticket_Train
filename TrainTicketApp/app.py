from datetime import datetime
from flask import Flask, redirect, render_template, request, send_file, url_for
from models import db, Buchung
from sqlalchemy.exc import IntegrityError
from reportlab.pdfgen import canvas

import tempfile


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zugreisen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        zugnummer = request.form.get('zugnummer')
        abfahrtsort = request.form.get('abfahrtsort')
        zielort = request.form.get('zielort')
        abfahrtszeit = datetime.strptime(request.form.get('abfahrtszeit'), '%Y-%m-%dT%H:%M')
        preis = float(request.form.get('preis'))

        neue_buchung = Buchung(name=name, zugnummer=zugnummer, abfahrtsort=abfahrtsort, zielort=zielort, abfahrtszeit=abfahrtszeit, preis=preis)

        db.session.add(neue_buchung)
        try:
            db.session.commit()
            return redirect(url_for('buchung_bestätigt', buchungs_id=neue_buchung.id))
        except IntegrityError:
            db.session.rollback()
            return redirect(url_for('index'))
    else:
        buchungen = Buchung.query.filter_by(storniert=False).all()
        return render_template('index.html', buchungen=buchungen)

@app.route('/stornieren/<int:buchungs_id>')
def stornieren(buchungs_id):
    buchung = Buchung.query.get_or_404(buchungs_id)
    buchung.storniert = True
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/rechnung/<int:buchungs_id>')
def rechnung(buchungs_id):
    buchung = Buchung.query.get_or_404(buchungs_id)
    response = create_pdf(buchung)
    return response

@app.route('/buchung-bestätigt/<int:buchungs_id>')
def buchung_bestätigt(buchungs_id):
    return render_template('booking_confirmation.html', buchungs_id=buchungs_id)

def create_pdf(buchung):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    filepath = temp_file.name
    c = canvas.Canvas(filepath)

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(300, 800, "Rechnung für Ihre Buchung")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Buchungsnummer: {buchung.id}")

    # Trennlinie
    c.line(50, 760, 550, 760)

    # Buchungsdetails
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

    return send_file(filepath, as_attachment=True)



if __name__ == '__main__':
    app.run(debug=True)

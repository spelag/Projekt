from datetime import datetime
from app import db
from werkzeug.security import check_password_hash, generate_password_hash

class User(db.Model):
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), primary_key=True, index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# class Patient(db.Model):
#     id= db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(120), nullable=False)
#     email = db.Column(db.String(120), index=True, unique=True, nullable=False)
#     phone_number = db.Column(db.String(12), unique=True, nullable=False)
#     doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
#     vaccine_doses = db.relationship('Vaccine_Dose', backref='patient')


class Match(db.Model):
    id= db.Column(db.Integer, primary_key=True)
    winner = db.Column(db.String(120), nullable=False) # mogoc s tem?? patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))  
    winner_points = db.Column(db.Integer, nullable=False)
    loser_points = db.Column(db.Integer, nullable=False)
    match_date = db.Column(db.DateTime(timezone=True), default=datetime.now)
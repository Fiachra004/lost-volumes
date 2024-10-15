from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_bootstrap import Bootstrap
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, SelectField, StringField
from wtforms.validators import InputRequired, Length
from werkzeug.utils import secure_filename
from flask_wtf.file import FileAllowed
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Folder_data.db'
app.config['FILE_FOLDER'] = 'files'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
bootstrap = Bootstrap(app)
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

USERNAME = 'LostVolumes'
PASSWORD = '$2a$12$8OqPA0U4sK4e3ADMUjNnceFXu66zAXF1EqcAfOjug4Gl0w6PF5uyu'

class Folder(db.Model):
    __tablename__ = 'folders'
    folder_name = db.Column(db.String(60), primary_key=True)
    elements = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    files = db.relationship('File', backref='folder', lazy=True)

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(60), nullable=False)
    name_stripped = db.Column(db.String(60), nullable=False)
    thumbnail = db.Column(db.String(60), nullable=False)
    folder_name = db.Column(db.String(60), db.ForeignKey('folders.folder_name'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True))

class FolderForm(FlaskForm):
    name = StringField("Folder Name", validators=[InputRequired(), Length(min=2, max=20)])
    submit = SubmitField("Add Folder")

class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    thumbnail = FileField("Thumbnail", validators=[InputRequired(), FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField("Upload File")
    folder_name = SelectField(u'Folder', coerce=str)  

def name_stripper(file_name):
    base_name = os.path.splitext(file_name)[0]
    clean_name = base_name.replace('_', ' ')
    return clean_name

@app.route('/', methods=['GET', 'POST'])
def Login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and bcrypt.check_password_hash(PASSWORD, password):
            session['logged_in'] = True
            return redirect(url_for('HomePri'))
    return render_template('LoginPage.html')

@app.route('/Home')
def HomePub():
    folders = Folder.query.all()
    return render_template('HomePub.html', folders=folders)

@app.route('/Upload', methods=['GET', 'POST'])
def HomePri():
    if 'logged_in' in session:
        upload_form = UploadFileForm()
        folder_form = FolderForm()
        upload_form.folder_name.choices = [(folder.folder_name, folder.folder_name) for folder in Folder.query.all()]
        folders = [folder.folder_name for folder in Folder.query.all()]

        if folder_form.validate_on_submit():
            folder_name = folder_form.name.data
            new_folder = Folder(folder_name=folder_form.name.data, created_at=func.now())
            if folder_name not in folders:
                db.session.add(new_folder)
                db.session.commit()
                return redirect(url_for('HomePri'))

        if upload_form.validate_on_submit():
            file = upload_form.file.data
            thumbnail = upload_form.thumbnail.data
            folder_name = upload_form.folder_name.data
            filename = secure_filename(file.filename)
            clean_name = name_stripper(filename)
            thumbnail_filename = secure_filename(thumbnail.filename)
            file.save(os.path.join(app.config['FILE_FOLDER'], filename))
            thumbnail.save(os.path.join(app.config['THUMBNAIL_FOLDER'], thumbnail_filename))
            new_file = File(file_name=filename, name_stripped=clean_name, thumbnail=thumbnail_filename, folder_name=folder_name, created_at=func.now())
            db.session.add(new_file)


            folder = Folder.query.filter_by(folder_name=folder_name).first()
            if folder:
                folder.elements += 1
            db.session.commit()

            return redirect(url_for('HomePri'))

        folders = Folder.query.all()
        return render_template('HomePri.html', upload_form=upload_form, folder_form=folder_form, folders=folders)
    else:
        return redirect(url_for('Login'))

@app.route('/thumbnails/<path:filename>')
def thumbnails(filename):
    return send_from_directory('thumbnails', filename)

@app.route('/Files/<path:filename>')
def Files(filename):
    return send_from_directory('Files', filename)
    
@app.route('/get_files/<folder_name>', methods=['GET'])
def get_files(folder_name):
    folder = Folder.query.filter_by(folder_name=folder_name).first()
    if folder:
        files = File.query.filter_by(folder_name=folder_name).all()
        file_names = [file.file_name for file in files]
        file_thumbnail = [file.thumbnail for file in files]
        clean_name = [file.name_stripped for file in files]
        return {'files': file_names, 'clean_name': clean_name, 'thumbnail': file_thumbnail}
    else:
        return {'files': []}, 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0')

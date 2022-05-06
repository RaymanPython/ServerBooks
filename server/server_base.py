from flask import Flask
from flask import request, abort, render_template, redirect, url_for, flash
import json
import sqlite3
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec
import datetime
from sqlalchemy import orm
from data.users import User
from data.users import Books
from data import db_session
from flask import json
from forms.user import RegisterForm
from forms.Search import SearchForm
from forms.Login import LoginForm
from flask import send_from_directory
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, SelectField
from flask_login import login_required
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
import os

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
# папка для сохранения загруженных файлов
UPLOAD_FOLDER = 'uploads'
# расширения файлов, которые разрешено загружать
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'html', 'jpg', 'jpeg', 'word'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

@app.route('/all_books')
def all_books():
    db_sess = db_session.create_session()
    books = []
    for book in db_sess.query(Books).all():
        books.append(book.link())
    return render_template('all_books.html', books=books)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route('/search', methods=['GET'])
def search():
    # form = SearchForm()
    search = request.args.get("search")
    db_sess = db_session.create_session()
    books = []
    for book in db_sess.query(Books).filter((Books.name.like(f'%{search}%') | Books.about.like(f'%{search}%'))).all():
        books.append(book.link())
    return render_template('all_books.html', books=books)


def save_base(filename, about="", user_id=0):
    name_text = '.'.join(filename.split('.')[:-1])
    db_sess = db_session.create_session()
    book = db_sess.query(Books).filter(Books.name == name_text).first()
    print(book)
    if book == None:
        book = Books()
        book.name = name_text
        book.about = about
        book.author_id = user_id
        book.text = filename
        db_sess.add(book)
        db_sess.commit()
        return True
    else:
        return False


def allowed_file(filename):
    """ Функция проверки расширения файла """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        # проверим, передается ли в запросе файл
        if 'file' not in request.files:
            # После перенаправления на страницу загрузки
            # покажем сообщение пользователю
            flash('Не могу прочитать файл')
            return redirect(request.url)
        file = request.files['file']
        # Если файл не выбран, то браузер может
        # отправить пустой файл без имени.
        if file.filename == '':
            flash('Нет выбранного файла')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # безопасно извлекаем оригинальное имя файла
            filename = file.filename
            # сохраняем файл
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # если все прошло успешно, то перенаправляем
            # на функцию-представление `download_file`
            # для скачивания файла
            if save_base(filename, about=request.form['about'], user_id=current_user.id):
                return redirect(url_for('download_file', name=filename))
            else:
                return render_template('error.html')
    return render_template('files.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)

@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/users_all')
def users_all():
    db_sess = db_session.create_session()
    users = []
    for user in db_sess.query(User).all():
        users.append(str(user))
    return render_template('all_users.html', users=users)


@app.before_first_request
def startup():
    db_session.global_init("db/blogs.db")


if __name__ == "__main__":
    app.run()

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey, or_
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
#from flask_login import LoginManager
import urllib.parse
import re
import os
from goodreads import client
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

is_prod = os.environ.get('IS_HEROKU', None)
if is_prod:
    dburi = os.environ.get('DATABASE_URL') + '?sslmode=require'
else:
    dburi = 'postgresql://postgres:postgres@localhost/bookshelf'

app.config['SQLALCHEMY_DATABASE_URI']=dburi

db = SQLAlchemy(app)

association_table = db.Table('association',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

music_association_table = db.Table('music_association',
    db.Column('music_id', db.Integer, db.ForeignKey('music.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)

class Book(db.Model):
    __tablename__="books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(400), nullable=False)
    author = db.Column(db.String(400), nullable=False)
    year = db.Column(db.Integer)
    dewey = db.Column(db.String(20))
    goodreads_url = db.Column(db.String(512))
    series = db.Column(db.String(300))
    status = db.Column(db.String(300))
    categories = db.relationship("Category", secondary=association_table, lazy='subquery',
                        backref=db.backref('books', lazy=True))

    def __init__(self, title, author, year, dewey, goodreads_url, series, status):
        self.title = title
        self.author = author
        self.year = year
        self.dewey = dewey
        self.goodreads_url = goodreads_url
        self.series = series
        self.status = status

class Category(db.Model):
    __tablename__="categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), unique=True)

    def __init__(self, name):
        self.name = name

class Music(db.Model):
    __tablename__="music"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(400), nullable=False)
    artist = db.Column(db.String(400), nullable=False)
    year = db.Column(db.Integer)
    format = db.Column(db.String(50))
    spotify_id = db.Column(db.String(512))
    status = db.Column(db.String(300))
    genres = db.relationship("Genre", secondary=music_association_table, lazy='subquery',
                        backref=db.backref('music', lazy=True))

    def __init__(self, title, artist, year, format, spotify_id, status):
        self.title = title
        self.artist = artist
        self.year = year
        self.format = format
        self.spotify_id = spotify_id
        self.status = status

class Genre(db.Model):
    __tablename__="genres"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), unique=True)

    def __init__(self, name):
        self.name = name

#login_manager = LoginManager()
#login_manager.init_app(app)

@app.route("/")
@app.route("/home")
@app.route("/index")
def index():
    books = Book.query.order_by(Book.id.desc()).limit(10).all()
    return render_template("index.html", books = books)

@app.route("/books", methods=['POST','GET'])
def books():
    category = None
    if request.method == "POST" and request.form["category"] != "_all_":
        category = request.form["category"]
        books = Book.query.join(Category, Book.categories).filter(Category.name == category).all()
    else:
        books = Book.query.limit(50).all()

    categories = Category.query.order_by(Category.name).all()
    count = Book.query.count()

    return render_template("books.html", count = count, books = books, categories = categories, category = category)

@app.route("/book/<int:id>")
def book(id):
    try:
        book = Book.query.filter(Book.id == id).first()
        goodreads_info = None

# TODO: Goodreads API no longer active - need to swap out for openlibrary.org
#
#        if book.goodreads_url:
#            #extract goodreads ID from url - eg https://www.goodreads.com/book/show/6452796-drive
#            goodreads_id = re.findall(r'\d+', book.goodreads_url)[0]
#            gc = client.GoodreadsClient(os.environ.get("GOODREADS_KEY"), os.environ.get("GOODREADS_SECRET"))
#            goodreads_info = gc.book(goodreads_id)

        return render_template("book.html", book = book, goodreads_info = goodreads_info)
    except NoResultFound:
        books = Book.query.order_by(Book.id.desc()).limit(10).all()
        return render_template("index.html", len = len(books), books = books)


@app.route("/update/<int:id>")
def update(id):
    book = Book.query.filter(Book.id == id).first()
    current_categories = [cat.name for cat in book.categories]
    categories = Category.query.order_by(Category.name).all()
    #dodgy hack
    if book.year == 0:
        book.year = ""

    return render_template("update.html", book = book, categories = categories, current_categories = current_categories)

@app.route("/update_success", methods=["POST"])
def update_success():
    if request.method == "POST":
        book = Book.query.filter(Book.id == request.form["id"]).first()

        book.title = request.form["title"]
        book.author = request.form["author"]

        year = request.form["year"]
        #dodgy hack
        if year == "":
            year = 0
        book.year = year

        book.dewey = request.form["dewey"]
        book.goodreads_url = request.form["goodreads_url"]
        book.series = request.form["series"]
        book.status = request.form["status"]

        #clear current categories and add new/changed ones
        categories = request.form.getlist("categories")
        book.categories = []
        for cat in categories:
            book.categories.append(Category.query.filter_by(id=cat).first())

        db.session.commit()
        return render_template("update_success.html")

@app.route("/search", methods=['POST','GET'])
def search():
    if request.args and "q" in request.args:
        args = request.args
        query = urllib.parse.unquote_plus(args["q"])
        books = Book.query.filter(or_(Book.title.ilike("%" + query + "%"), Book.author.ilike("%" + query +"%"))).all()
        albums = Music.query.filter(or_(Music.title.ilike("%" + query + "%"), Music.artist.ilike("%" + query +"%"))).all()
        return render_template("search.html", bookcount = len(books), musiccount = len(albums), books = books, albums = albums)
    else:
        return render_template("search.html", bookcount=0, musiccount=0)

@app.route("/add_book")
def add_book():
    categories = Category.query.order_by(Category.name).all()

    return render_template("add.html", categories = categories)

@app.route("/add_music")
def add_music():
    genres = Genre.query.order_by(Genre.name).all()

    return render_template("add_music.html", genres = genres)


@app.route("/category")
def category():
    categories = Category.query.order_by(Category.name).all()

    return render_template("category.html", categories = categories)

@app.route("/category_success", methods=['POST'])
def category_success():
    if request.method == "POST":
        category_name = request.form["category_name"]

        category = Category(category_name)
        db.session.add(category)
        db.session.commit()

        categories = Category.query.all()
        return render_template("category.html", categories = categories)

@app.route("/genres")
def genres():
    genres = Genre.query.order_by(Genre.name).all()

    return render_template("genres.html", genres = genres)

@app.route("/genre_success", methods=['POST'])
def genre_success():
    if request.method == "POST":
        genre_name = request.form["genre_name"]

        genre = Genre(genre_name)
        db.session.add(genre)
        db.session.commit()

        genres = Genre.query.all()
        return render_template("genres.html", genres = genres)


@app.route("/success", methods=['POST'])
def success():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]

        if year == "":
            year = 0

        dewey = request.form["dewey"]
        goodreads_url = request.form["goodreads_url"]
        categories = request.form.getlist("categories")
        series = request.form["series"]
        status = request.form["status"]

        data = Book(title, author, int(year), dewey, goodreads_url, series, "In Bookshelf")
        for cat in categories:
            data.categories.append(Category.query.filter_by(id=cat).first())

        db.session.add(data)
        db.session.commit()

        return render_template("success.html")


@app.route("/music_success", methods=['POST'])
def music_success():
    if request.method == "POST":
        title = request.form["title"]
        artist = request.form["artist"]
        year = request.form["year"]

        if year == "":
            year = 0

        format = request.form["format"]
        spotify_id = request.form["spotify_id"]
        genres = request.form.getlist("genres")
        status = request.form["status"]

        data = Music(title, artist, int(year), format, spotify_id, status)
        for genre in genres:
            data.genres.append(Genre.query.filter_by(id=genre).first())

        db.session.add(data)
        db.session.commit()
    
        return render_template("success.html")

@app.route("/music", methods=['POST','GET'])
def music():
    genre = None
    if request.method == "POST" and request.form["genre"] != "_all_":
        genre = request.form["genre"]
        music = Music.query.join(Genre, Music.genres).filter(Genre.name == genre).all()
    else:
        music = Music.query.limit(50).all()

    genres = Genre.query.order_by(Genre.name).all()
    count = Music.query.count()

    return render_template("music.html", count = count, music = music, genres = genres, genre = genre)


@app.route("/album/<int:id>")
def album(id):
    try:
        music = Music.query.filter(Music.id == id).first()
        album_info = None

        if music.spotify_id:
            spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
            album_info = spotify.album(music.spotify_id)

        return render_template("album.html", music = music, album_info = album_info)
    except NoResultFound:
        books = Book.query.order_by(Book.id.desc()).limit(10).all()
        return render_template("index.html", len = len(books), books = books)


@app.route("/update_album/<int:id>")
def update_album(id):
    album = Music.query.filter(Music.id == id).first()
    current_genres = [genre.name for genre in album.genres]
    genres = Genre.query.order_by(Genre.name).all()
    #dodgy hack
    if album.year == 0:
        album.year = ""

    return render_template("update_album.html", album = album, genres = genres, current_genres = current_genres)

@app.route("/update_album_success", methods=["POST"])
def update_album_success():
    if request.method == "POST":
        album = Music.query.filter(Music.id == request.form["id"]).first()

        album.title = request.form["title"]
        album.artist = request.form["artist"]

        year = request.form["year"]
        #dodgy hack
        if year == "":
            year = 0
        album.year = year

        album.format = request.form["format"]
        album.spotify_id = request.form["spotify_id"]
        album.status = request.form["status"]

        #clear current categories and add new/changed ones
        genres = request.form.getlist("genres")
        album.genres = []
        for genre in genres:
            album.genres.append(Genre.query.filter_by(id=genre).first())

        db.session.commit()
        return render_template("update_success.html")

if __name__ == '__main__':
    app.debug = True
    app.run()

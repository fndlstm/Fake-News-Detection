from flask import Flask, render_template, url_for, request, flash
import joblib
import re
import string
import pandas as pd
import requests
from decouple import config
from googleapiclient.discovery import build
from PIL import Image
import pytesseract
import os
import csv
import sys
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import InputRequired, Email
from flask_mail import Message, Mail


app = Flask(__name__)
Model = joblib.load('E:/CUIISB/FYP/FND/Implementation/Code/Model.pkl')
NEWS_API_KEY = config('NEWS_API_KEY')
COUNTRY = 'us'
api_key = config('CUSTOM_SEARCH_API_KEY')
resource = build("customsearch", 'v1', developerKey=api_key).cse()
pytesseract.pytesseract.tesseract_cmd = config(r'TESSERACT_PATH')
path = os.getcwd()
UPLOAD_FOLDER = os.path.join(path, config('U_FOLDER'))
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = config('CONTACT_FORM_KEY')
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = config(r'EMAIL_USER')
app.config["MAIL_PASSWORD"] = config(r'EMAIL_PASSWORD')
app.config["MAIL_DEFAULT_SENDER"] = config(r'EMAIL_USER')
mail = Mail(app)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/sourceauth')
def sourceauth():
    return render_template("sourceauth.html")


@app.route('/latestnews')
def latestnews():
    news_articles = get_latest_news()
    return render_template("latestnews.html", news_articles=news_articles)


@app.route('/factcheck')
def factcheck():
    return render_template("factcheck.html")


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm(request.form)
    if request.method == 'POST':
        if form.validate() == False:
            return render_template("contact.html", form = form)
        elif form.validate() == True:
            msg = Message('Thank You For Reaching Out to Us',
                          recipients=['fnd.hassankhan@yahoo.com'], 
                          body="Thank You for reaching out to us regarding your query. We are always happy to hear from our users and will try our best to answer any queries and suggestions.")
            mail.send(msg)
            msg = Message(subject="New Query/Suggestion Submitted at FND", 
                          recipients=[config(r'EMAIL_USER')], 
                          body="""
                          From: %s <%s>
                          %s
                          """ % (form.name.data, form.email.data, form.message.data))
            mail.send(msg)
            return render_template("contact.html", success = True)
    elif request.method == 'GET':
        return render_template("contact.html", form = form)


def wordpre(text):
    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub("\\W", " ", text)  # remove special chars
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub('<.*?>+', '', text)
    text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub('\n', '', text)
    text = re.sub(r'\w*\d\w*', '', text)
    return text


def get_latest_news():
    news_data = requests.get(
        f'https://newsapi.org/v2/top-headlines?country={COUNTRY}&apiKey={NEWS_API_KEY}').json()
    return news_data['articles']


def ocr_core(filename):
    text = pytesseract.image_to_string(Image.open(filename))
    return text


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired("Please enter your name.")])
    email = StringField("Email", validators=[InputRequired("Please enter your email address."), Email("Please enter your email address in the correct form (e.g. example@xyz.com).")])
    message = TextAreaField("Message", validators=[InputRequired("Please fill the message form.")])
    submit = SubmitField("Submit")


@app.route('/detectfakenews', methods=['POST'])
def pre():
    if request.method == 'POST':
        txt = request.form['txt']
        txt = wordpre(txt)
        txt = pd.Series(txt)
        result = Model.predict(txt)
        return render_template("index.html", result=result, flag=True)
    return ''


@app.route('/uploadimage', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template("index.html")
        file = request.files['file']
        if file.filename == '':
            return render_template("index.html")
        if file:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            extracted = ocr_core(file)
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return render_template("index.html", extracted=extracted, uimg=True)
        else:
            return render_template("index.html")
        return ''


@app.route('/sourceauthenticate', methods=['POST'])
def source_auth():
    if request.method == 'POST':
        txt = request.form['txt']
        txt = txt.lower()
        csv_file = csv.reader(open('unreliablesources.csv', "r"), delimiter=",")
        for row in csv_file:
            if txt in row[0].lower():
                return render_template("sourceauth.html", flag=True, domain=row[0], mbfcfactual=row[3], mbfcurl=row[4], misinfome=row[5], logically=row[6], ournews=row[7], satire=row[8], result=1)
            elif txt in row[1].lower():
                return render_template("sourceauth.html", flag=True, domain=row[0], mbfcfactual=row[3], mbfcurl=row[4], misinfome=row[5], logically=row[6], ournews=row[7], satire=row[8], result=1)
            elif txt in row[2].lower():
                return render_template("sourceauth.html", flag=True, domain=row[0], mbfcfactual=row[3], mbfcurl=row[4], misinfome=row[5], logically=row[6], ournews=row[7], satire=row[8], result=1)
        return render_template("sourceauth.html", result=0)
    return '' 


if __name__ == "__main__":
    app.run(debug=True)

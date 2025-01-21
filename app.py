from flask import Flask, render_template, redirect, request, g
import sqlite3
from openai import OpenAI
import os

app = Flask(__name__)

# This function returns the database. If the database has not been created yet, it creates it and
# stores it in Flask's special global variable `g`.
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("feedback.db")
    return db

# Similar to get_db, this function get's the OpenAI client, which is used to interact with the
# OpenAI API.
def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    client = OpenAI(api_key=api_key)
    return client

# This function is decorated to return the index page when the user visits the root URL.
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# This function is decorated to handle the feedback form submission's POST-request, storing the
# feedback in the database, and renders thanks page when complete.
@app.route('/feedback', methods=['POST'])
def feedback():
    feedback = request.form.get('feedback')
    db = get_db()
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS feedback (feedback TEXT)") # Only happens once
    cur.execute("INSERT INTO feedback (feedback) VALUES (?)", (feedback,))
    db.commit()
    return render_template('thanks.html')


@app.route('/summarize_feedback', methods=['GET'])
def summarize_feedback():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT feedback FROM feedback")
    feedbacks = cur.fetchall()
    feedbacks = [feedback[0] for feedback in feedbacks]
    feedbacks = "\n".join(feedbacks)
    openai_client = get_openai_client()
    completion = openai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Summarize the submitted feedbacks (new-line separated). Identify key topics about the assignment for the class to discuss. Format as a bullet list in html without code fences.",
            },
            {
                "role": "user",
                "content": feedbacks,
            }
        ],
        model="gpt-3.5-turbo",
    )
    summary = completion.choices[0].message.content
    return render_template('summary.html', summary=summary)

# This function is called when the app is done running.
# It closes the database connection.
# The OpenAI client does not need to be closed.
@app.teardown_appcontext
def close_connection(exception):
    db = get_db()
    db.close()
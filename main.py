import json
from datetime import datetime, timedelta

import peewee
import pytz
from flask import Flask
from flask import Response
from flask import render_template
from icalendar import Calendar
from icalendar import Event

from manager import TimeTableManager
from models import db, Course, Lecture, update_course_lectures

app = Flask(__name__)

# Manager
manager = TimeTableManager(
    week_range=range(33, 51),
    year=2016,
    list_url='http://timeplan.uia.no/swsuiah/restrict/no/default.aspx',
    show_url='http://timeplan.uia.no/swsuiah/XMLEngine/default.aspx'
)

# DB setup
db.connect()
try:
    db.create_tables([Course, Lecture])

    courses = manager.load_courses_retry()
    with db.atomic() as txn:
        for code, name in courses.items():
            Course.create(code=code, name=name)
except peewee.OperationalError:
    print('DB already created')


# Routes
@app.route('/')
def index():
    courses = json.dumps([{'code': c.code, 'name': c.name} for c in Course.select()])
    return render_template('index.html', courses=courses)


@app.route('/<courses>.ics')
def courses_ics(courses):
    course_codes = courses.split('+')

    courses = Course.select().where(Course.code << course_codes)
    for course in courses:
        if course.last_update < datetime.now() - timedelta(days=2):
            lectures = manager.load_lectures(course.code)
            if len(lectures):
                update_course_lectures(course.code, lectures)

    cal = Calendar()
    cal.add('prodid', '-//UiA Timeplaner//timeplaner.olav.it//')
    cal.add('version', '1.0')

    lectures = Lecture.select().where(Lecture.course << courses)
    for lecture in lectures:
        event = Event()
        event.add('uid', '{}@timeplaner.olav.it'.format(lecture.id))
        event.add('summary', lecture.description)
        event.add('dtstart', lecture.time_from.replace(tzinfo=pytz.timezone('Europe/Oslo')))
        event.add('dtend', lecture.time_to.replace(tzinfo=pytz.timezone('Europe/Oslo')))

        if lecture.lecturer:
            event.add('organizer', lecture.lecturer)
        if lecture.location:
            event.add('location', lecture.location)

        cal.add_component(event)

    return Response(cal.to_ical(), content_type='text/calendar; charset=utf-8')


if __name__ == "__main__":
    app.run()

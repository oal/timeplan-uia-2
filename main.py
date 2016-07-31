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
# TODO: Provide a config file instead of hard coding year and weeks here.
manager = TimeTableManager(
    week_range=range(32, 52),
    year=2016,
    list_url='http://timeplan.uia.no/swsuiah/restrict/no/default.aspx',
    show_url='http://timeplan.uia.no/swsuiah/XMLEngine/default.aspx'
)

# DB setup, create tables if they don't already exist.
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
    """
    Index page. Renders a template and sends course data as JSON so we fetch that upon page load as well.

    :return:
    """

    courses = json.dumps([{'code': c.code, 'name': c.name} for c in Course.select()])
    return render_template('index.html', courses=courses)


@app.route('/<courses>.ics')
def courses_ics(courses):
    """
    Takes a +-separated list of course codes and returns an ics calendar.

    :param courses: str
    :return:
    """

    course_codes = courses.split('+')

    # Get courses from DB and make sure no more than five courses are selected
    # (that could end up being really slow).
    courses = Course.select().where(Course.code << course_codes)
    if len(courses) > 5:
        return Response('Too many courses selected', status=400)

    # Check if any of the requested courses need to be updated.
    # Update if last update was more than two days ago.
    for course in courses:
        if course.last_update < datetime.now() - timedelta(days=2):
            lectures = manager.load_lectures(course.code)
            if len(lectures):
                update_course_lectures(course.code, lectures)

    # Create iCal calendar.
    cal = Calendar()
    cal.add('prodid', '-//UiA Timeplaner//timeplaner.olav.it//')
    cal.add('version', '2.0')

    # Load all lectures from DB and add them to the calendar.
    # Feel free to improve this, I'm not that familiar with the iCal spec.
    lectures = Lecture.select().where(Lecture.course << courses).order_by(Lecture.time_from.asc())
    for lecture in lectures:
        event = Event()
        event.add('uid', '{}@timeplaner.olav.it'.format(lecture.id))
        event.add('summary', '{}\n{}'.format(lecture.description, lecture.lecturer))
        event.add('dtstart', lecture.time_from.replace(tzinfo=pytz.timezone('Europe/Oslo')))
        event.add('dtend', lecture.time_to.replace(tzinfo=pytz.timezone('Europe/Oslo')))

        if lecture.location:
            event.add('location', lecture.location)

        cal.add_component(event)

    return Response(cal.to_ical(), content_type='text/calendar; charset=utf-8')


if __name__ == "__main__":
    app.run(port=4999)

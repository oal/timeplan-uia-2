import json
from datetime import datetime, timedelta

import peewee
from flask import Flask
from flask import Response
from flask import render_template
from icalendar import Calendar
from icalendar import Event

from manager import TimeTableManager
from models import db, Course, Lecture, update_course_lectures, Request
import config

app = Flask(__name__)

# Manager
manager = TimeTableManager(
    week_range=config.WEEKS,
    year=config.YEAR,
    list_url=config.LIST_URL,
    show_url=config.SHOW_URL
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

try:
    db.create_tables([Request])
except peewee.OperationalError:
    print('Request tracking table already created')

# Routes
@app.route('/')
def index():
    """
    Index page. Renders a template and sends course data as JSON so we fetch that upon page load as well.

    :return:
    """

    courses = json.dumps([{'code': c.code, 'name': c.name} for c in Course.select()])

    now = datetime.now()
    stats_week = Request\
        .select(peewee.fn.COUNT(Request.id).alias('num_requests'))\
        .where(Request.time > now - timedelta(days=7))

    stats_total = Request\
        .select(peewee.fn.COUNT(Request.id).alias('num_requests'))

    return render_template(
        'index.html',
        courses=courses,
        stats_week=stats_week,
        stats_total=stats_total,
    )


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

    # Set a name for the calendar.
    calendar_name = 'Timeplan for '
    if len(courses) == 1:
        calendar_name += courses[0].name
    else:
        calendar_name += ', '.join(course_codes[0:-1]) + ' og ' + course_codes[-1]

    cal.add('name', calendar_name)
    cal.add('tz', '+00')
    cal.add('x-wr-timezone', 'Europe/Oslo')

    # Load all lectures from DB and add them to the calendar.
    # Feel free to improve this, I'm not that familiar with the iCal spec.
    lectures = Lecture.select().where(Lecture.course << courses).order_by(Lecture.time_from.asc())
    for lecture in lectures:
        event = Event()
        event.add('uid', '{}@timeplaner.olav.it'.format(lecture.id))
        event.add('summary', '{}\n{}'.format(lecture.description, lecture.lecturer))
        event.add('dtstart', lecture.time_from)
        event.add('dtend', lecture.time_to)

        if lecture.location:
            event.add('location', lecture.location)

        cal.add_component(event)

    # Traffic tracking
    with db.atomic() as txn:
        for c in courses:
            Request.create(course=c)

    return Response(cal.to_ical(), content_type='text/calendar; charset=utf-8')


if __name__ == "__main__":
    app.run(port=4999)

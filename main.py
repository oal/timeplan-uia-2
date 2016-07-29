import json
from datetime import datetime, timedelta

import peewee
from flask import Flask
from playhouse.shortcuts import model_to_dict

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
def hello():
    return "Hello World!"


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


@app.route('/api/course/<code>')
def api_course(code):
    course = Course.get(code=code)
    if course.last_update < datetime.now() - timedelta(days=7):
        lectures = manager.load_lectures(course.code)
        if len(lectures):
            update_course_lectures(course.code, lectures)

    return json.dumps(
        [model_to_dict(lecture) for lecture in Lecture.select(Lecture.course == course)],
        default=json_serial
    )


if __name__ == "__main__":
    app.run()


'''
with db.atomic() as txn2:
    for lecture in manager.load_lectures('TFL115-G'):
        print(Lecture.create(
            course=Course.get(Course.code == 'TFL115-G'),
            **lecture
        ))
'''
# print(manager.load_courses_retry())
# print()

'''
[
    "'TFL115-G/Forel/01 Engelsk veiledning",
    '2016-11-18', '14:15',
    '2016-11-18', '16:00',
    'Almlie, Gunvor Sofia',
    'GRM C2 042 aud'
], ["'TFL115-G/Forel/01 Faglig veiledning gruppeprosjekt", '2016-11-18', '14:15', '2016-11-18', '16:00', 'Vehus, Tore, Nilsen, Tom V.', 'GRM C2 036 aud']]
'''

from datetime import datetime
import peewee
from playhouse.sqlite_ext import SqliteExtDatabase

db = SqliteExtDatabase('timetables.db')


class Course(peewee.Model):
    code = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    last_update = peewee.DateTimeField(default=datetime(1970, 1, 1))

    class Meta:
        database = db


class Lecture(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    course = peewee.ForeignKeyField(Course)
    description = peewee.CharField()
    time_from = peewee.DateTimeField()
    time_to = peewee.DateTimeField()
    lecturer = peewee.CharField(null=True)
    location = peewee.CharField(null=True)

    class Meta:
        database = db


def update_course_lectures(course_code, lectures):
    course = Course.get(code=course_code)
    course.last_update = datetime.now()
    course.save()

    with db.atomic() as txn:
        Lecture.delete().where(Lecture.course == course)
        for lecture in lectures:
            uid = lecture['description'] + str(lecture['time_from'])
            Lecture.create(id=abs(hash(uid)), course=course, **lecture)

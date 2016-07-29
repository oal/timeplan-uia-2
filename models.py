from datetime import datetime
import peewee

db = peewee.SqliteDatabase('timetables.db')


class Course(peewee.Model):
    code = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    last_update = peewee.DateTimeField(default=datetime(1970, 1, 1))

    class Meta:
        database = db


class Lecture(peewee.Model):
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

    with db.atomic() as txn:
        Lecture.delete().where(Lecture.course == course)
        for lecture in lectures:
            Lecture.create(course=course, **lecture)
            course.last_update = datetime.now()
            course.save()

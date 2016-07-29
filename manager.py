from collections import OrderedDict

from datetime import datetime
import requests
import lxml.html
from lxml.cssselect import CSSSelector
from time import sleep, strptime, mktime
import re


def extract_form_data(resp):
    tree = lxml.html.fromstring(resp.text)
    data = {}
    for field in CSSSelector('input')(tree):
        data[field.get('name')] = field.get('value') or ''
    for field in CSSSelector('input[checked]')(tree):
        data[field.get('name')] = field.get('value') or ''
    for field in CSSSelector('select option[selected]')(tree):
        data[field.getparent().get('name')] = field.get('value') or ''

    return data


class TimeTableManager(object):
    def __init__(self, week_range, year, list_url, show_url):
        self.session = requests.Session()
        self.weeks = ';'.join(str(w) for w in week_range)
        self.year = year
        self.list_url = list_url
        self.show_url = show_url

    def load_course_list(self):
        resp = self.session.get(self.list_url)
        data = extract_form_data(resp)
        data['__EVENTTARGET'] = 'LinkBtn_modules'
        data['__EVENTARGUMENT'] = ''

        # Sleep because if we run another request too quickly it responds with "no action taken".
        # Maybe due to multi threading and session data not persisted yet.
        sleep(2)

        return self.session.post(self.list_url, data=data)

    def load_courses(self):
        """
        Returns an OrderedDict of course code / course name mappings.

        :return: OrderedDict
        """

        resp = self.load_course_list()
        tree = lxml.html.fromstring(resp.content)
        code_regexp = re.compile(r'[A-Z]{1,3}-?[0-9]{3}-?[1G]?')

        course_codes = OrderedDict()
        for course in CSSSelector('#dlObject option')(tree):
            code = course.get('value')
            clean_code = code_regexp.findall(code)
            if not clean_code:
                continue

            course_codes[clean_code[0]] = ' '.join(course.text.strip().split(' ')[1:])

        return course_codes

    def load_courses_retry(self, retries=3):
        """
        Sometimes "no action taken" is returned, so this is a helper to try a few times before giving up.

        :param retries: int
        :return: OrderedDict
        """

        for i in range(retries):
            courses = self.load_courses()
            if courses:
                return courses

    def load_lectures(self, course_code):
        resp = self.session.post('{}?ModuleByWeek&p1=;{};&p2={}'.format(self.show_url, course_code, self.weeks))
        tree = lxml.html.fromstring(resp.content)

        lectures = []
        for row in CSSSelector('tr.tr2')(tree):
            cells = CSSSelector('td')(row)
            lecture_date = '{} 2016'.format(cells[1].text)
            start, end = cells[2].text.split('-')

            time_from = strptime('{} {}'.format(lecture_date, start), '%d %b %Y %H.%M')
            time_to = strptime('{} {}'.format(lecture_date, end), '%d %b %Y %H.%M')

            description = cells[3].text
            location = cells[4].text
            lecturer = cells[5].text

            lectures.append({
                'description': description,
                'time_from': datetime.fromtimestamp(mktime(time_from)),
                'time_to': datetime.fromtimestamp(mktime(time_to)),
                'lecturer': lecturer,
                'location': location
            })

        return lectures

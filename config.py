YEAR = 2016
IS_SPRING = False

if IS_SPRING:
    WEEKS = range(0, 33)
    LIST_URL = 'http://timeplan.uia.no/swsuiav/restrict/no/default.aspx'
    SHOW_URL = 'http://timeplan.uia.no/swsuiav/XMLEngine/default.aspx'
else:
    WEEKS = range(32, 52)
    LIST_URL = 'http://timeplan.uia.no/swsuiah/restrict/no/default.aspx'
    SHOW_URL = 'http://timeplan.uia.no/swsuiah/XMLEngine/default.aspx'




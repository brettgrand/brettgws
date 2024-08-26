# brettgws

BrettGrand's Google Work Space facilitators

Some classes for facilitating access to GoogleWorkSpace.  There are may of
these out there, but like a lot of these sorts of things I needed to force
myself to learn the API so I implemented some wrappers.

Authentication seems to be the biggest headache.  While there are plenty of
tutorials out there they all seem to eventually point back to the online
[docs](https://developers.google.com/people/quickstart/python) which like
most of these things does a good job of documenting the basics but quickly
falls short as soon as you start trying to do something slightly more
compliciated.

## Scopes

The Google client is based around OAuth2 so you need to understand
[scopes](https://developers.google.com/identity/protocols/oauth2/scopes),
which simply put is the permission level for that particular service.
So for example for a client to get read/write access to a
[Calendar](https://developers.google.com/identity/protocols/oauth2/scopes#calendar)
you would need https://www.googleapis.com/auth/calendar scope access, or
https://www.googleapis.com/auth/calendar.readonly for Calendar read-only or for
[Sheets](https://developers.google.com/identity/protocols/oauth2/scopes#sheets)
you would want to request https://www.googleapis.com/auth/spreadsheets for
read-write, https://www.googleapis.com/auth/spreadsheets.readonly for read-only
and so on.

## Access

The brettgws authentication is built around the \_\_GWSAccess class which is
hidden as a module singleton and accessed through the gws object.  So to access
you would want to do:
```python
from brettgws.access import gws
```
and go from there.  Why a singleton?  There just didn't seem to be any reason
to need distinct authentication for each support class.  So just pass in your
authentication file and the scopes you require and everything then has central
access.
Because the scope URL's can be a pain to remember the gws will take 'simplified'
names which is just a key to a simple map so you can:
```python
gws.append_scopes('sheets')
```
rather than
```python
gws.append_scopes('https://www.googleapis.com/auth/spreadsheets')
```
although of course the URL will work as well.  But the scope append will be
handled by the support classes if you use those.

### Access Flow

brettgws is intended to support a desktop application so it is expecting
a credential file as specified [here](https://developers.google.com/people/quickstart/python#authorize_credentials_for_a_desktop_application).
Eventually support for service accounts will be added but not there yet.

So we need access to the client credential secrets file, but we can also
cache the authentication results so we dont have to go through the login
pages each time.  For that a disctinct cache file needs to be pointed to.
It will be created if needed and removed when scopes or credentials change.
So a general authentiction setup flow for an app to get read-write access
to Calendar and read-only to Sheets would look like:
```python
from brettgws.access import gws

# in this case path_to_secrets and path_to_cache are pathlib.Path or str
# to a secrets file or cache file respectively
gws.client_secrets = path_to_secrets
gws.cred_cache = path_to_cache

# add in the scopes we care about, we can also set to just these via
# gws.scopes = ['calendar', 'sheets-ro'] but that will clear any other
# scopes in the cred_cache, using append just means 'add if necessary
# otherwise use what's there'.
gws.append_scopes('calendar')
gws.append_scopes('sheets-ro')
# could also gws.append_scopes('calendar', 'sheets-ro') or
# gws.append_scopes(['calendar', 'sheets-ro'])

# actually does the authentication exchange
gws.connect()

```

### Services
Once you have an authenticated session, to do anything useful you need to get
the relevant [service](https://developers.google.com/sheets/api/reference/rest#service-endpoint)
which is the REST URL endpoint.  In the Google client parlance its their
Request object to make your actual REST calls.
In brettgws you request the service from the gws object like so:
```python
service = gws.get_service("sheets", "v4")
```
and then you can build your request.  The gws object will attempt to connect
if not already in that state when requesting a service.

But dealing with services and the specifics to the requests is a real pain and
exactly what the support classes are there to hide from you.  You will need to
specify the secrets and credential cache files but the support classes will
take care of everything else.

## Support Classes
Objects to facilitate interacting with the GWS services.
So far supporting Sheets and Calendar, and even then not absolutely everything
as this is a WIP based on functional need.

At the heart, the support classes use dataclasses to represent the resources,
requets, and responses.  Could have done something more dynamic like the Google
client does but this is meant to simplify dealing with the API so explicitly
defining the fields makes it very clear what is there, and also to see what
types they can support.

### Calendar
The [Calendar](https://developers.google.com/calendar/api/guides/overview)
API is fairly simple.  The [CalendarList](https://developers.google.com/calendar/api/v3/reference/calendarList)
is your entry point if you have no other object identification as it can
get a list of all calendars to the current authenticated user.  And then
there are the individual [Calendars](https://developers.google.com/calendar/api/v3/reference/calendars)
and [Events](https://developers.google.com/calendar/api/v3/reference/events).
So some examples:
```python
import brettgws.calendar

# we're looking for a specfic calendar to add an event to, all I know
# is that it's called 'My 1on1' in the calendar.
looking_for = 'My 1on1'
# get everything
clist = brettgws.calendar.CalendarList.list()

cal = next((c for c in clist if c.summary == looking_for), None)
if cal is None:
    print('was not there')
    return
# if we knew the id beforehand we could just do:
# cal = brettgws.calendar.Calendar.get(id)

# lets add an all-day event
ev = brettgws.calendar.Event()
ev.summary = 'this will be all day'
ev.description = 'differentiated by GWS by whether the start/end has just a day or a time'
ev.location = 'somewhere'

# add the event 1 day from today and lasts 3 days
start = datetime.date.today()
start = start.replace(day=start.day + 1)
end = start + datetime.timedelta(days=3)
ev.set_duration(start,end)
brettgws.calendar.Event.insert(cal, ev)

```

### Sheets
Spreadsheets are of course more complicated than a calendar so the sheets
[API](https://developers.google.com/sheets/api/reference/rest) is also more
complicated.  With the [Calendar](#Calendar) being simple it can be done as
some static methods on the dataclass representation of the resources.  Sheets
are more complicated so while dataclass representations of the resources exist
it is intended to go through the support classes.

#### A1 Notation
Google sheets addresses cells in either [A1](https://developers.google.com/sheets/api/guides/concepts#expandable-1)
or [R1C1](https://developers.google.com/sheets/api/guides/concepts#expandable-2).
The sheets API for the most part expects A1 so that's what brettgws supports.
R1C1 is useful for relative addressing but otherwise unneccesary.
To facilitate A1 manipulation the brettgws.sheets.a1.GoogleSheetsA1Notiation
class is provided which can handle the translation to/from strings and also
being able to add or remove rows and columns.  There is also the concept of
'unbounded' which is 'all' or 'to the end'. So if you specify a row but no
columns then that means all columns.  If you specify a start but no end then
it means all available to the end.  So if we have a sheet with columns A:M then
just specifying column I will mean I,J,K,L,M.

#### Spreadsheet
A [Spreadsheet](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets)
is the whole document that encapsulates some number (at least 1) of Sheets, which
is the general grid of cells we expect.  The global properties covering all Sheets
are specified at this level and also the unique ID in the spreadsheet URL.
A Sheet is specified by a Spreadsheet ID and a Sheet ID or Index.  Typically you
would create a Spreadsheet object using the known GUID and then getting the
Sheet you want from there.  So for example:
```python
from brettgws.sheet.spreadsheet import GoogleSpreadSheet
my_sheet_id = 'blahblahsomeuniqueidinthesheeturl'
ssheet = GoogleSpreadSheet(my_sheet_id)
ssheet.get()

# just want a small set of data with major dimension of ROWS
data = ssheet.getValues("Data!B2:C5", "ROWS")
# data.values[0][2] is cell B4
# data.values[1][1] is cell C3

# get the Sheet object labeled 'Data', same on refereced above in A1
sheet = ssheet\['Data'\]
```
See doc on [ValueRange](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values#resource:-valuerange)
to understand the major dimension.  Effectively its whether the list of lists
is in row or column major format.

### Sheet
The [Sheet](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#Sheet)
is the page of cells that we know and love.  There can be any number of sheets
contained in a Spreadsheet but the current cell limit for a Spreadsheet is
10 million across all of the contained sheets.  Conceptually you work with an
individual sheet so that is how the class is designed, even though in reality
all of the Sheet operations are at the Spreadsheet level as far as GWS is
concerned.  At this leve you can query and alter dimensions and get/set data.
The sheets API allows bundling operations into a batch so the Sheet class allows
building up a sequence of commands until terminating with an .execute().
So something like:
```python
# assume we grabbed the ssheet as above
sheet = ssheet\['Data'\]
# add an extra row and 2 columns
sheet.updateRequests().expandDimensions(1,2).execute()
# reduce the sheet by 1 row
sheet.updateRequests().reduceDimension(1,"ROWS").execute()
# hard set the dimensions to 15 rows and 22 columns
sheet.updateRequests().reshapeDimensions(15,22).execute()
# get the same data as in the above Spreadsheet example
# the Sheet ID will be automatically added to the request
data = sheet.getValues("B2:C5")
# lets clear our the B5 and C5 values
sheet.clearValues("B5:C5")
# lets update the values at B3:C3
# the dimension argument can take a variety of shorthand
# notations like R, C, COLS
from brettgws.sheets.resources import ValueRange
range = ValueRange("B3:C3", "R", \[\["New Data B3", "New Data C3"\]\])
sheet.updateValues(range)
```







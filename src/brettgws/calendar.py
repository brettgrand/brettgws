
from dataclasses import dataclass, field, asdict
from typing import List, Self, Tuple
import datetime
from zoneinfo import ZoneInfo
from functools import partial

from .resources import GoogleWorkSpaceResourceBase

from .access import gws

# do this as module level or a parent class instance?
# simpler at module level and achieves the same thing
_get_service = partial(gws.get_service, "calendar", "v3")

@dataclass
class CalendarList(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/calendar/api/v3/reference/calendarList#resource-representations
    Note that the GWS client will trim out any attribute with a value of None so use that
    as the empty/default
    """
    kind: str|None = field(default=None)
    etag: str|None = field(default=None)
    id: str|None = field(default=None)
    summary: str|None = field(default=None)
    description: str|None = field(default=None)
    location: str|None = field(default=None)
    timeZone: str|None = field(default=None)
    summaryOverride: str|None = field(default=None)
    colorId: str|None = field(default=None)
    backgroundColor: str|None = field(default=None)
    foregroundColor: str|None = field(default=None)
    hidden: bool|None = field(default=None)
    selected: bool|None = field(default=None)
    accessRole: str|None = field(default=None)
    defaultReminders: List[dict]|None = field(default=None)
    notificationSettings: dict|None = field(default=None)
    primary: bool|None = field(default=None)
    deleted: bool|None = field(default=None)
    conferenceProperties: dict|None = field(default=None)

    def __bool__(self) -> bool:
        return self.kind is not None and self.kind == "calendar#calendarListEntry" and bool(self.etag) and bool(self.id)
    
    def __str__(self) -> str:
        if self:
            return f"{self.id}:{self.summary}"
        return "<empty>"
    
    def __repr__(self) -> str:
        return f"{str(self.__class__)}:{str(self)}"
    
    @staticmethod
    def list(minAccessRole: str = "",
             showDeleted: bool = False,
             showHidden: bool = False) -> List[Self]:
        """
        Helper wrapper for CalendarList::list
        This is the entry point for pulling out available calendars.  Start here to get
        a list of calendars with their calendIds, which can then be used for further operations.
        https://developers.google.com/calendar/api/v3/reference/calendarList/list
        """
        page_token = None
        clist = []
        args = {"pageToken": page_token, "showDeleted": showDeleted, "showHidden": showHidden}
        if minAccessRole:
            if minAccessRole in ["freeBusyReader", "owner", "reader", "writer"]:
                args["minAccessRole"] = minAccessRole
            else:
                raise ValueError(f"Invalid CalendarList::list() minAccessRole: {minAccessRole}")
        # cache the method locally rather than look up on each loop iteration
        method = _get_service().calendarList().list
        while True:
            response = method(**args).execute()
            if response:
                for entry in response['items']:
                    clist.append(CalendarList(**entry))
                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break
        return clist

@dataclass
class Calendar(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/calendar/api/v3/reference/calendars#resource-representations
    Typically you'd interact with this via ::get and an id, which is usually someone's email address
    """
    kind: str|None = field(default=None)
    etag: str|None = field(default=None)
    id: str|None = field(default=None)
    summary: str|None = field(default=None)
    description: str|None = field(default=None)
    location: str|None = field(default=None)
    timeZone: ZoneInfo|str|None = field(default=None)
    conferenceProperties: dict|None = field(default=None)

    def __post_init__(self) -> None:
        self.fixup()

    def __bool__(self) -> bool:
        return self.kind is not None and self.kind == "calendar#calendar" and bool(self.etag) and bool(self.id)
    
    def __str__(self) -> str:
        if bool(self):
            return f"{self.summary}<{self.id}>"
        else:
            return "<empty>"
        
    def __repr__(self) -> str:
        return f"{str(self.__class__)}:{str(self)}"
    
    def to_base(self) -> dict:
        self.fixup()
        b = asdict(self)
        b['timeZone'] = str(self.timeZone) if self.timeZone is not None else None
        return b

    def fixup(self) -> None:
        if self.timeZone is not None and not isinstance(self.timeZone,ZoneInfo):
            self.timeZone = ZoneInfo(str(self.timeZone))

    @staticmethod
    def get(id: str = "primary") -> Self:
        """
        https://developers.google.com/calendar/api/v3/reference/calendars/get
        Get the calendar entry with the associated ID.  The 'primary' default is
        the currently authenticated user.  Not sure how that works with a service account? 
        """
        i = str(id)
        if i:
            response = _get_service().calendars().get(calendarId=i).execute()
            return Calendar(**response)
        return Calendar()
    
    def refresh(self) -> None:
        """
        Pull from upstream to update any fields that may have changed.
        """
        if self.id:
            response = _get_service().calendars().get(calendarId=str(self.id)).execute()
            self.update_fields(**response)

    def update(self,
               description: bool = True,
               location: bool = True,
               timeZone: bool = True) -> List[str]:
        """
        https://developers.google.com/calendar/api/v3/reference/calendars/update
        Update calendar fields.  Apparently summary is always updated where
        description, location, and timeZone are optional.
        This will update the current self with the current status upstream.
        """
        if not self.id:
            raise RuntimeError("Calendar::update must have a valid ID field")
        body = {'summary': self.summary}
        updated = []
        if location:
            body['location'] = self.location
        if description:
            body['description'] = self.description
            body['summary'] = self.summary
        if timeZone:
            body['timeZone'] = str(self.timeZone)
        if body:
            response = _get_service().calendars().get(calendarId=str(self.id), body=body).execute()
            if response:
                updated = self.update_fields(**response)
        return updated

@dataclass
class EventDateTime(GoogleWorkSpaceResourceBase):
    """
    Class for facilitating dealing with Event start/stop dicts.
    They use distinct fields to signal all-day ('date') vs specific
    day/time ('dateTime') so easier to carry both here and work out
    at runtime what is needed.
    Will default to dateTime when both are specified although that should
    never happen
    """
    date: datetime.date|str|None = field(default=None)
    dateTime: datetime.datetime|str|None = field(default=None)
    timeZone: ZoneInfo|str|None = field(default=None)

    def __bool__(self) -> bool:
        return bool(self.date) or bool(self.dateTime)
    
    def __str__(self) -> str:
        s = "<empty>"
        if self.dateTime:
            s = str(self.dateTime)
        elif self.date:
            s = str(self.date)
        if self.timeZone:
            s = f'{s}:{str(self.timeZone)}'
        return s

    def __post_init__(self) -> None:  
        self.fixup()

    def fixup(self) -> None:
        if self.date is not None and not isinstance(self.date, datetime.date):
            self.date = datetime.date.fromisoformat(str(self.date))
        if self.dateTime is not None and not isinstance(self.dateTime,datetime.datetime):
            self.dateTime = datetime.datetime.fromisoformat(str(self.dateTime)).replace(microsecond=0)
        if self.timeZone is not None and not isinstance(self.timeZone,ZoneInfo):
            self.timeZone = ZoneInfo(str(self.timeZone))
        # 'date' means all-day, can't have 'date' and 'dateTime' so one has to take precedence
        if self.dateTime and self.date:
            self.date = None
        
    def values(self) -> Tuple[datetime.date|datetime.datetime|None,ZoneInfo|None]:
        return (self.dateTime if self.dateTime else self.date, self.timeZone)
    
    def to_base(self) -> dict:
        """
        Convert any date/datetime/ZoneInfo into the strings needed by GWS
        Really annoying that datetime.__str__ returns datetime.isoformat(' ')
        as GWS needs the 'T' separator
        GWS expects either date or dateTime to be there, not both so strip out
        one or all
        """
        self.fixup()
        base = { 'date': self.date.isoformat() if self.date else None,
                 'dateTime': self.dateTime.isoformat() if self.dateTime else None,
                 'timeZone': str(self.timeZone) if self.timeZone else None }
        
        for k in ['date', 'dateTime', 'timeZone']:
            if base[k] is None:
                del base[k]

        return None if not base else base


@dataclass
class Event(GoogleWorkSpaceResourceBase):
    """
    https://developers.google.com/calendar/api/v3/reference/events#resource-representations
    Representation of a calendar event.
    """
    kind: str|None = field(default=None)
    etag: str|None = field(default=None)
    id: str|None = field(default=None)
    status: str|None = field(default=None)
    htmlLink: str|None = field(default=None)
    created: datetime.datetime|str|None = field(default=None)
    updated: datetime.datetime|str|None = field(default=None)
    summary: str|None = field(default=None)
    description: str|None = field(default=None)
    location: str|None = field(default=None)
    colorId: str|None = field(default=None)
    creator: dict[str,str,str,bool]|None = field(default=None)
    organizer: dict[str,str,str,bool]|None = field(default=None)
    start: EventDateTime|dict|None = field(default=None)
    end: EventDateTime|dict|None = field(default=None)
    endTimeUnspecified: bool|None = field(default=None)
    recurrence: List[str]|None = field(default=None)
    recurringEventId: str|None = field(default=None)
    originalStartTime: EventDateTime|dict|None = field(default=None)
    transparency: str|None = field(default=None)
    visibility:str|None = field(default=None)
    iCalUID: str|None = field(default=None)
    sequence: int|None = field(default=None)
    attendees: List[dict]|None = field(default=None)
    attendeesOmitted: bool|None = field(default=None)
    extendedProperties: dict|None = field(default=None)
    hangoutLink: str|None = field(default=None)
    conferenceData: dict|None = field(default=None)
    gadget: dict|None = field(default=None)
    anyoneCanAddSelf: bool|None = field(default=None)
    guestsCanInviteOthers: bool|None = field(default=None)
    guestsCanModify: bool|None = field(default=None)
    guestsCanSeeOtherGuests: bool|None = field(default=None)
    privateCopy: bool|None = field(default=None)
    locked: bool|None = field(default=None)
    reminders: dict|None = field(default=None)
    source: dict|None = field(default=None)
    workingLocationProperties: dict|None = field(default=None)
    outOfOfficeProperties: dict|None = field(default=None)
    focusTimeProperties: dict|None = field(default=None)
    attachments: List[dict]|None = field(default=None)
    eventType: str|None = field(default=None)

    def __post_init__(self) -> None:
        self.fixup()

    def fixup(self) -> None:
        if self.created is not None and not isinstance(self.created,datetime.datetime):
            self.created = datetime.datetime.fromisoformat(str(self.created)).replace(microsecond=0)
        if self.updated is not None and not isinstance(self.updated,datetime.datetime):
            self.updated = datetime.datetime.fromisoformat(str(self.updated)).replace(microsecond=0)
        if self.start is not None and not isinstance(self.start, EventDateTime):
            self.start = EventDateTime(**dict(self.start))
        if self.end is not None and not isinstance(self.end, EventDateTime):
            self.end = EventDateTime(**dict(self.end))
        if self.originalStartTime is not None and not isinstance(self.originalStartTime,EventDateTime):
            self.originalStartTime = EventDateTime(**dict(self.originalStartTime))

    def __bool__(self) -> bool:
        return self.kind is not None and self.kind == "calendar#event" and bool(self.etag) and bool(self.id)
    
    def __str__(self) -> str:
        ret = "<empty>"
        if self:
            start, stz, end, _ = self.duration()
            ret = f"{self.summary}<{self.id}>"
            if start:
                ret += f"({str(start)}-->{str(end)}:{str(stz)})"
        return ret

    def all_day(self) -> bool:
        """
        Is this an all-day event?  That is, is it just date components and not datetime?
        """
        return self.start.date is not None and self.end.date is not None
    
    def duration(self) -> Tuple[datetime.date|datetime.datetime|None,ZoneInfo|None,
                                datetime.date|datetime.datetime|None,ZoneInfo|None]:
        """
        Return the current start/end values.  Because they can be date or datetime
        it does the selection for you.
        """
        return (*self.start.values(), *self.end.values())
    
    def set_duration(self, start: str|datetime.date|datetime.datetime,
                     end: str|datetime.date|datetime.datetime, tz: str|ZoneInfo|None = None) -> None:
        """
        Set the start and end date/time for the event.
        A date object signals all-day event (no time) and is a distict field from datetime
        so we need to work out what the intention is.  A start and end datetime with both
        at datetime.time.min (midnight) will consider all-day and convert to date
        Note that datetime is a subclass of date when comparing
        """
        s = start if isinstance(start,datetime.date) else str(start)
        if isinstance(s,str):
            s = datetime.datetime.fromisoformat(s).replace(microsecond=0)
        e = end if isinstance(end,datetime.date) else str(end)
        if isinstance(e,str):
            e = datetime.datetime.fromisoformat(e).replace(microsecond=0)
        if isinstance(s,datetime.datetime) and type(e) is datetime.date:
            s = s.date()
        if type(s) is datetime.date and isinstance(e,datetime.datetime):
            e = e.date()
        if isinstance(s,datetime.datetime):
            st = s.time()
            et = e.time()
            m = datetime.time.min
            if st == m and et == m:
                s = s.date()
                e = e.date()
        es = EventDateTime()
        ee = EventDateTime()
        if isinstance(s,datetime.datetime):
            es.dateTime = s
            ee.dateTime = e
        else:
            es.date = s
            ee.date = e
        t = None if tz is None else tz if isinstance(tz,ZoneInfo) else str(tz)
        if isinstance(t,str):
            t = ZoneInfo(t)
        es.timeZone = t
        ee.timeZone = t
        self.start = es
        self.end = ee

    def to_base(self) -> dict:
        """
        Convert any date/datetime/ZoneInfo into the strings needed by GWS
        Really annoying that datetime.__str__ returns datetime.isoformat(' ')
        as GWS needs the 'T' separator
        """
        self.fixup()
        b = asdict(self)
        if self.start:
            b['start'] = self.start.to_base()
        if self.end:
            b['end'] = self.end.to_base()
        if self.originalStartTime:
            b['originalStartTime'] = self.originalStartTime.to_base()
        if self.created:
            b['created'] = str(self.created)
        if self.updated:
            b['updated'] = str(self.updated)
        return b

    @staticmethod
    def list(calendar_id: str|Calendar = "primary", **kwargs) -> List[Self]:
        """
        https://developers.google.com/calendar/api/v3/reference/events/list
        Entry point for all calendar events.  Call this to get the list
        to then get the ID of a particular event.
        The calendar ID is required but the kwargs are the very large number
        of query parameters for this method so check the documentation.
        """
        method = _get_service().events().list
        page_token = None
        cid = calendar_id.id if isinstance(calendar_id,Calendar) else str(calendar_id)
        # we're being lazy with not specifying all of the query parameters
        # so need to ensure this particular one isnt present
        kwargs.pop('pageToken', None)
        # timeMin and timeMax are funny in that they MUST have the tz offset applied
        # so check here and adjust if possible
        tz = None
        if 'timeZone' in kwargs:
            kwtz = kwargs['timeZone']
            if kwtz:
                if isinstance(kwtz,ZoneInfo):
                    tz = kwtz
                    kwargs['timeZone'] = str(kwtz)
                else:
                    tz = ZoneInfo(str(kwtz))
            else:
                del kwargs['timeZone']
        for t in ['timeMin', 'timeMax']:
            if t in kwargs:
                tm = kwargs[t]
                if tm:
                    tmdt = tm if isinstance(tm, datetime.datetime) else datetime.datetime.fromisoformat(str(tm))
                    tmdt = tmdt.replace(microsecond=0)
                    tzinfo = tmdt.tzinfo if hasattr(tmdt, 'tzinfo') else tz if tz is not None else ZoneInfo('UTC')
                    tstr = tmdt.astimezone(tzinfo).isoformat()
                    kwargs[t] = tstr
                else:
                    del kwargs[t]
        events = []
        while True:
            response = method(calendarId=cid, pageToken=page_token, **kwargs).execute()
            for e in response['items']:
                events.append(Event(**e))
            page_token =  response.get('nextPageToken', None)
            if not page_token:
                break
        return events

    @staticmethod
    def get(calendar_id: str|Calendar, event_id: str|Self,
            maxAttendees: int = 0, timeZone: str|ZoneInfo|None = None) -> Self:
        """
        https://developers.google.com/calendar/api/v3/reference/events/get
        Get the event associated with the calendar and event IDs
        """
        cid = calendar_id.id if isinstance(calendar_id,Calendar) else str(calendar_id)
        eid = event_id.id if isinstance(event_id,Event) else str(event_id)
        request = {'calendarId': cid, 'eventId': eid }
        if maxAttendees > 0:
            request['maxAttendees'] = maxAttendees
        if timeZone:
            request['timeZone'] = str(timeZone)
        response = _get_service().events().get(**request).execute()
        return Event(**response)
    
    @staticmethod
    def delete(calendar_id: str|Calendar, event_id: str|Self,
               sendUpdates: str = "all") -> None:
        """
        https://developers.google.com/calendar/api/v3/reference/events/delete
        Delete the event with the associated calendar and event IDs
        """
        if sendUpdates not in ["all", "externalOnly", "none"]:
            raise ValueError(f"Invalid Event::delete() sendUpdates value: {sendUpdates}")
        cid = calendar_id.id if isinstance(calendar_id,Calendar) else str(calendar_id)
        eid = event_id.id if isinstance(event_id,Event) else str(event_id)
        _get_service().events().delete(calendarId = cid, eventId = eid, sendUpdates = sendUpdates).execute()
        
    @staticmethod
    def insert(calendar_id: str|Calendar, event: Self|dict,
               sendUpdates: str = "",
               maxAttendees: int = 0,
               supportsAttachments: bool = False,
               conferenceDataVersion: int = 0) -> Self:
        """
        https://developers.google.com/calendar/api/v3/reference/events/insert
        Insert a new event into the specified calendar
        """
        cid = calendar_id.id if isinstance(calendar_id,Calendar) else str(calendar_id)
        request = {"calendarId": cid, "body": event.trim() if isinstance(event,Event) else event,
                   "supportsAttachments" : supportsAttachments,
                   "conferenceDataVersion" : 0 if not conferenceDataVersion else 1}
        if maxAttendees > 0:
            request['maxAttendees'] = maxAttendees
        if sendUpdates:
            if sendUpdates not in ["all", "externalOnly", "none"]:
                raise ValueError(f"Invalid Event::insert() sendUpdates value: {sendUpdates}")
            request['sendUpdates'] = sendUpdates
        
        response = _get_service().events().insert(**request).execute()
        # if an Event was passed in, fill that out, otherwise return a new object
        if isinstance(event, Event):
            event.update_fields(**response)
            return event
        return Event(**response) 
    
    @staticmethod
    def update(calendar_id: str|Calendar, event: Self|dict,
               sendUpdates: str = "",
               maxAttendees: int = 0,
               supportsAttachments: bool = False,
               conferenceDataVersion: int = 0) -> None:
        """
        https://developers.google.com/calendar/api/v3/reference/events/update
        Update the event on the specified calendar.
        """
        cid = calendar_id.id if isinstance(calendar_id,Calendar) else str(calendar_id)
        body = event.trim() if isinstance(event,Event) else dict(event)
        request = {"calendarId": cid, "eventId": body['id'], "body": body,
                   "sendUpdates": sendUpdates, "supportsAttachments" : supportsAttachments,
                   "conferenceDataVersion" : 0 if not conferenceDataVersion else 1}
        if maxAttendees > 0:
            request['maxAttendees'] = maxAttendees
        if sendUpdates:
            if sendUpdates not in ["all", "externalOnly", "none"]:
                raise ValueError(f"Invalid Event::update() sendUpdates value: {sendUpdates}")
            request['sendUpdates'] = sendUpdates
        e = _get_service().events().insert(**request).execute()
        if isinstance(event,Event):
            event.update_fields(**e)
            return event
        return Event(**e)
        


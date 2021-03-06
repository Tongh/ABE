#!/usr/bin/env python3
"""Sub event helper functions
helpful inspiration: https://gist.github.com/jason-w/4969476
"""

from datetime import date, datetime, timedelta

import dateutil.parser
import pytz
from dateutil.rrule import rrule

from abe import database as db
from abe.helper_functions.converting_helpers import mongo_to_dict


def duplicate_query_check(sub_event_dict, parent_event):
    """checks whether a dictionary has the same field-value pair as a parent event
    used to check for duplicate information in sub_events and their parent events
    """
    parent_event_dict = mongo_to_dict(parent_event)
    fields_to_pop = []
    for field in sub_event_dict:
        if field in parent_event_dict:
            if sub_event_dict[field] == parent_event_dict[field]:
                fields_to_pop.append(field)
    for field in fields_to_pop:
        sub_event_dict.pop(field)

    return(sub_event_dict)


def create_sub_event(received_data, parent_event):
    """creates an edited sub event in a recurring series for the first time
    """
    sub_event_dict = duplicate_query_check(received_data, parent_event)
    rec_event = db.RecurringEventExc(**sub_event_dict)
    parent_event.update(add_to_set__sub_events=rec_event)
    parent_event.reload()

    return(rec_event)


def update_sub_event(received_data, parent_event, sub_event_id, ics=False):
    """edits a sub_event that has already been created

    sub_event_id        if the update is not coming from an ics feed:
                            - will be an objectid
                        if the update is coming from an ics feed:
                            - will be a rec_id (datetime object)
    """
    def convert_timezone(a):
        return a.replace(tzinfo=pytz.UTC) if isinstance(a, datetime) else a
    for sub_event in parent_event.sub_events:
        if not ics:  # if this update is not coming from an ics feed
            # if the sub_event to be updated's id matches the id of the received_data
            if sub_event['_id'] == sub_event_id:
                updated_sub_event_dict = create_new_sub_event_defintion(
                    mongo_to_dict(sub_event), received_data, parent_event)
                updated_sub_event = db.RecurringEventExc(**updated_sub_event_dict)
                parent_event.update(pull__sub_events___id=sub_event_id)
                parent_event.update(add_to_set__sub_events=updated_sub_event_dict)
                if not updated_sub_event_dict['forever']:
                    parent_event.recurrence_end = find_recurrence_end(parent_event)
                parent_event.save()
                parent_event.reload()
                return(updated_sub_event)
        else:  # if this update is coming from an ics feed
            sub_event_compare = convert_timezone(sub_event["rec_id"])
            if sub_event_compare == sub_event_id:
                updated_sub_event_dict = create_new_sub_event_defintion(
                    mongo_to_dict(sub_event), received_data, parent_event)
                updated_sub_event = db.RecurringEventExc(**updated_sub_event_dict)
                parent_event.update(pull__sub_events__rec_id=sub_event_id)
                parent_event.update(add_to_set__sub_events=updated_sub_event_dict)
                if not updated_sub_event_dict['forever']:
                    parent_event.recurrence_end = find_recurrence_end(parent_event)
                parent_event.save()
                parent_event.reload()
                return(updated_sub_event)


def sub_event_to_full(sub_event_dict, event):
    """expands a sub_event definition to have all fields full_Calendar requires
    uses its parent definition to fill in the blanks
    """
    recurring_def_fields = ["end_recurrence", "recurrence", "sub_events"]
    date_fields = ['start', 'end', 'rec_id']
    for field in event:
        if field not in sub_event_dict and field not in recurring_def_fields:
            if field == 'id':
                sub_event_dict["sid"] = str(event[field])
            elif field == 'ics_id':
                sub_event_dict[field] = str(event[field])
            elif field in date_fields:
                sub_event_dict[field] = dateutil.parser.parse(str(sub_event_dict[field]))
            else:
                sub_event_dict[field] = event[field]
    sub_event_dict['labels'] = event['labels']
    sub_event_dict["id"] = sub_event_dict.pop("_id")
    return(sub_event_dict)


def access_sub_event(parent_event, sub_event_id):
    """gets the sub_event from a parent_event and returns it
    """
    for sub_event in parent_event['sub_events']:
        if sub_event['_id'] == str(sub_event_id):
            return(sub_event)


def create_new_sub_event_defintion(sub_event, updates, parent_event):
    """based on the old sub_event definition and updates submitted
    generates a new sub_event definition
    """
    sub_event.update(updates)
    sub_event = duplicate_query_check(sub_event, parent_event)
    return(sub_event)


def instance_creation(event, start=None, end=None):
    """
    Generate a list of datetime objects of when recurring events should occur.
    Uses rrule from dateutils.
    Only recurrences between start and end, if supplied, are created.
    """

    rec_type_list = ['YEARLY', 'MONTHLY', 'WEEKLY', 'DAILY']

    day_list = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']

    recurrence = event.recurrence

    def ensure_date_time(d):
        return dateutil.parser.parse(d) if not isinstance(d, datetime) and not isinstance(d, date) else d

    def convert_timezone(d):
        return d.replace(tzinfo=None) if isinstance(d, datetime) else d

    rFrequency = rec_type_list.index(recurrence['frequency'])
    rStart = convert_timezone(ensure_date_time(event['start']))
    if recurrence['frequency'] == 'YEARLY':
        # extracts the month and day from the date
        rByMonth = int(rStart.month)
        rByMonthDay = int(rStart.day)
        rByDay = None
    else:
        if 'by_month_day' in recurrence:
            rByMonthDay = [int(x) for x in recurrence['by_month_day']]
        else:
            rByMonthDay = None

        if 'by_month' in recurrence:
            rByMonth = [int(x) for x in recurrence['by_month']]
        else:
            rByMonth = None
        if 'by_day' in recurrence:
            rByDay = []
            for i in recurrence['by_day']:
                rByDay.append(day_list.index(i))
        else:
            rByDay = None

    rInterval = int(recurrence['interval'])
    rCount = int(recurrence['count']) if 'count' in recurrence else None
    if rCount is None:
        if recurrence.forever:
            rUntil = convert_timezone(ensure_date_time(end)) if end is not None else None
        else:
            rUntil = convert_timezone(ensure_date_time(recurrence['until'])) if 'until' in recurrence else end
    else:
        rUntil = None

    rule_list = list(rrule(freq=rFrequency, count=rCount, interval=rInterval, until=rUntil, bymonth=rByMonth,
                           bymonthday=rByMonthDay, byweekday=rByDay, dtstart=rStart))
    return(rule_list)


def find_recurrence_end(event):
    """
    Finds the last occurrence of an event and returns the day after.
    """
    rule_list = instance_creation(event)
    event_end = rule_list[-1] + timedelta(hours=24)
    return event_end

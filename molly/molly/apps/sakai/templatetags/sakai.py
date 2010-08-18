from __future__ import division
from datetime import datetime
from django import template

register = template.Library()

@register.filter
def from_sakai_timestamp(value):
    return datetime.fromtimestamp(value/1000)

@register.filter    
def places_left(value):
    return (value["maxNoOfAttendees"]-len(value["attendees"]))

@register.filter
def signup_status(ts, event):
    if ts["signedUp"]:
        return 'signed-up'
    elif not places_left(ts):
        if event["allowWaitList"]:
            
            return 'waiting-list'
        else:
            return 'full'
    else:
        return 'available'

@register.filter
def signup_status_human(value):
    return {'signed-up': 'Signed Up', 'waiting-list': 'Waiting List', 'full': 'Full', 'available': 'Available'}[value]
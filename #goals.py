#!/usr/bin/python

""" #goals
A goals review tool for todo.txt users who do a weekly review of tasks, projects, and goals.

USAGE:
    python \#goals.py [todo.txt] [done.txt] [#goals.txt]

USAGE NOTES:
    Expects four parameters:
    1. Properly-formatted todo.txt file. See todotxt.com.
    2. Properly-formatted done.txt file. See todotxt.com.
    3. A #goals.txt file which lists one #goal followed by any number of +projects associated with it per line.
    4. The number of days you want to review. Defaults to 7 for a weekly review.

    See more on todo.txt here:
    http://todotxt.com

OUTPUT:
    Displays a count of how many tasks were completed associated with a goal categorized by project.

"""

from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import sys
from datetime import datetime, timedelta
import datetime
import time
import collections
import re

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from collections import OrderedDict

# Process arguments
try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('--todo', dest='todo_file', metavar='todo.txt', type=str, nargs='?',
                    help='Properly-formatted todo.txt file. See todotxt.com.')
    parser.add_argument('--done', dest='done_file', metavar='done.txt', type=str, nargs='?',
                    help='Properly-formatted done.txt file. See todotxt.com.')
    parser.add_argument('--goals', dest='goals_file', metavar='#goals.txt', type=str, nargs='?',
                    help='A #goals.txt file which lists one #goal followed by any number of +projects associated with it per line.')
    parser.add_argument('--days', dest='number_days_int', metavar='total days', type=int, nargs='?',
                    help='The number of days you want to review. Defaults to 7 for a weekly review.',
                    default=7)
    flags = parser.parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Hashtag Goals for Google Calendar'


__version__ = "1.0"
__date__ = "2016/03/17"
__updated__ = "2016/07/02"
__author__ = "Gina Trapani (ginatrapani@gmail.com)"
__copyright__ = "Copyright 2016, Gina Trapani"
__license__ = "GPL"
__history__ = """
1.0 - Initial version
"""

def hed_prefix(c):
    return c * "#"

def hed(text, level):
    return br(hed_prefix(level) + " " + text)

def br(text):
    return text + "\n"

def format_goal(goal):
    return re.sub(r"(?<=\w)([A-Z])", r" \1", goal)[1:]

def format_event(event, project):
    # event summary may or may not have +Project in it; display either way
    return event['summary'].replace(project, '').strip() + " " + project

def get_event_words(event):
    words = event['summary'].split()
    if 'description' in event: # not every event has a description
        words += event['description'].split()
    return words

def is_word_project(word):
    return word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+"

def main(argv):
    try:
        goal_projects = get_goal_projects(flags.goals_file)
    except ValueError as e:
        print (str(e))
        parser.print_help()
        sys.exit(2)

    last_x_days = get_last_x_days(flags.number_days_int)

    last_x_days_of_completions = get_last_x_days_of_completions(flags.done_file, last_x_days)
    last_x_days_of_completions_from_calendar = get_last_x_days_of_completions_from_calendar(get_gcal(flags.number_days_int))
    last_x_days_of_completions.extend(last_x_days_of_completions_from_calendar)

    project_completions = get_project_completions(last_x_days_of_completions)

    goal_completions = get_goal_completions(goal_projects, project_completions)

    # Next week's prioritizations
    upcoming_events = get_gcal(flags.number_days_int, False)
    project_prioritized = get_project_prioritized_tasks_and_events(flags.todo_file, upcoming_events)

    total_tasks_prioritized = get_total_prioritized_tasks(flags.todo_file)
    total_tasks_prioritized += get_total_scheduled_project_events(upcoming_events)

    goal_prioritized = get_goal_prioritized(goal_projects, project_prioritized)

    # Write report to buffer: For each item in goal_projects, print the goal, the number of tasks completed,
    #   then each project and the number of tasks completed
    try:
        goals_buf = StringIO.StringIO()
    except AttributeError:
        goals_buf = StringIO()

    goals_not_moved = []
    goals_moved = []
    goals_not_prioritized = []
    goals_prioritized = []

    most_progressed_project_total = 0
    most_progressed_projects = []

    for goal in goal_projects:
        total_done = 0
        if goal in goal_completions:
            total_done = len(goal_completions[goal])

        total_prioritized = 0
        if goal in goal_prioritized:
            total_prioritized = len(goal_prioritized[goal])

        goal_header = format_goal(goal) + " - " + str(total_done) + " done, " + str(total_prioritized) + " prioritized"
        goals_buf.write(hed(goal_header, 3))

        if total_done > 0:
            goals_buf.write(br(""))
            goals_buf.write(br("Completed:"))
        for project in goal_projects[goal]:
            if project in project_completions:
                for task in project_completions[project]:
                    goals_buf.write(br(task.strip()))
        if total_done > 0:
            goals_moved.append(goal)
            if total_done > most_progressed_project_total:
                most_progressed_project_total = total_done
        else:
            goals_buf.write(br("No completed tasks."))
            goals_not_moved.append(format_goal(goal))

        goals_buf.write(br(""))
        goals_buf.write(br("Prioritized:"))

        if total_prioritized > 0:
            for project in goal_projects[goal]:
                if project in project_prioritized:
                    goals_buf.write(br(project))
                    for task in project_prioritized[project]:
                        goals_buf.write(br("    " + task.strip()))
            goals_prioritized.append(goal)
        else:
            goals_buf.write(br("    " + "No prioritized tasks."))
            goals_not_prioritized.append(goal)

        goals_buf.write(br(""))

    # Check for multiple most-progressed goals
    for goal in goal_projects:
        total_done = 0
        if goal in goal_completions:
            total_done = len(goal_completions[goal])
            if total_done == most_progressed_project_total:
                most_progressed_projects.append(format_goal(goal))

    # Write summary buffer
    try:
        summary_buf = StringIO.StringIO()
    except AttributeError:
        summary_buf = StringIO()

    summary_buf.write(hed("Summary", 2))
    summary_buf.write(br(str(len(last_x_days_of_completions)) + " completed tasks moved " +
        str(len(goals_moved)) + " out of " + str(len(goal_projects)) + " goals forward."))
    if len(most_progressed_projects) > 0:
        summary_buf.write(br('Made the most progress on ' +
            ('%s' % ' & '.join(map(str, most_progressed_projects))) + '.'))
    if len(goals_not_moved) > 0:
        summary_buf.write(br('Made no progress on ' + ('%s' % ' & '.join(map(str, goals_not_moved))) + '.'))
    summary_buf.write(br(""))
    summary_buf.write(br(str(total_tasks_prioritized) + " tasks are prioritized which will move " +
        str(len(goals_prioritized)) + " out of " + str(len(goal_projects)) + " goals forward."))
    # Write list of goals that are not prioritized
    if len(goals_not_prioritized) > 0:
        summary_buf.write(br("Goals that are not prioritized:"))
        for goal in goals_not_prioritized:
            summary_buf.write(br("    " + format_goal(goal)))

    # Warnings
    try:
        warnings_buf = StringIO.StringIO()
    except AttributeError:
        warnings_buf = StringIO()
    # Completed project warnings
    warnings_buf.write(cross_check_projects(project_completions, goal_projects))
    # Prioritized project warnings
    warnings_buf.write(cross_check_projects(project_prioritized, goal_projects))

    # Output report
    # Title
    print(br(hed("Goal Review for the past " + str(flags.number_days_int) + " days", 1)))
    print(br("Generated " + datetime.datetime.today().strftime('%b %d, %Y at %H:%M	%Z')))
    # Summary
    print(summary_buf.getvalue())
    summary_buf.close()
    # Goals
    print (goals_buf.getvalue())
    goals_buf.close()
    # Warnings
    print (warnings_buf.getvalue())
    warnings_buf.close()

def get_total_prioritized_tasks(todotxt_file):
    total = 0
    f = open (todotxt_file, "r")
    for task in f:
        words = task.split()
        if words and words[0].startswith("("):
            total += 1
    f.close()
    return total

def get_total_scheduled_project_events(events):
    total = 0
    for event in events:
        words = get_event_words(event)
        for word in words:
            if is_word_project(word):
                total += 1
    return total

# Return an array of goals with total tasks completed.
def get_goal_completions(goal_projects, project_completions):
    goal_completions = {}
    goals = goal_projects.keys()
    for goal in goal_projects:
        for project in project_completions:
            if project in goal_projects[goal]:
                if goal not in goal_completions:
                    goal_completions[goal] = project_completions[project]
                else:
                    goal_completions[goal] = goal_completions[goal] + project_completions[project]
    return goal_completions

# Return an array of goals with total tasks completed.
def get_goal_prioritized(goal_projects, project_prioritized):
    goal_prioritized = {}
    goals = goal_projects.keys()
    for goal in goal_projects:
        for project in project_prioritized:
            if project in goal_projects[goal]:
                if goal not in goal_prioritized:
                    goal_prioritized[goal] = project_prioritized[project]
                else:
                    goal_prioritized[goal] = goal_prioritized[goal] + project_prioritized[project]
    return goal_prioritized

# Return the goal/project list as a dictionary of arrays goalProjects[goal] = projects[]
def get_goal_projects(goals_file):
    try:
        goal_projects = OrderedDict()
        f = open (goals_file, "r")
        for line in f:
            words = line.split()
            for index, word in enumerate(words):
                if index == 0:
                    # Goal
                    if word[0:1] == "#":
                        current_goal = word
                        goal_projects[current_goal] = []
                    else:
                        raise ValueError(br("GOALS FILE FORMAT ERROR: The first word on each line in %s should be a #goal, this word is %s."% (goals_file,word,)))
                else:
                    # Project
                    if word[0:1] == "+":
                        goal_projects[current_goal].append(word)
                    else:
                        raise ValueError(br("GOALS FILE FORMAT ERROR: Any words following a #goal on each line in %s should be a +project, this word is %s."% (goals_file,word,)))
        f.close()
        return goal_projects
    except IOError:
        print(br("ERROR: The file %s could not be read."% (goals_file, )))
        parser.print_help()
        sys.exit(2)

# Get the last X days as an array of todo.txt-formatted dates.
def get_last_x_days(number_days):
    today = datetime.date.today()
    last7Days = []
    for d in range(number_days):
        day_this_week = today - datetime.timedelta(days=d)
        last7Days.append(day_this_week.strftime('%Y-%m-%d'))
    return last7Days

# Return last 7 days of completed tasks from done.txt
def get_last_x_days_of_completions(done_file, last_x_days):
    try:
        last_x_days_of_completions = []
        f = open (done_file, "r")
        for line in f:
            words = line.split()
            if len(words) > 2 and words[1] in last_x_days:
                last_x_days_of_completions.append(line)
        f.close()
        return last_x_days_of_completions
    except IOError:
        print(br("ERROR:  The file named %s could not be read."% (done_file, )))
        parser.print_help()
        sys.exit(2)

# Return last x days of calendar events with project notations (tasks that were scheduled and completed).
def get_last_x_days_of_completions_from_calendar(events):
    last_x_days_of_completions = []
    for event in events:
        words = get_event_words(event)
        for word in words:
            if is_word_project(word):
                last_x_days_of_completions.append(format_event(event, word))
    return last_x_days_of_completions

# Return an array of projects with their associated tasks.
def get_project_completions(last_x_days_of_completions):
    project_completions = {}
    for task in last_x_days_of_completions:
        words = task.split()
        for word in words:
            if is_word_project(word):
                if word not in project_completions:
                    project_completions[word] = [task]
                else:
                    project_completions[word].append(task)
    return project_completions

# Return an array of projects with their associated tasks and events.
def get_project_prioritized_tasks_and_events(todotxt_file, events):
    project_prioritized = {}
    f = open (todotxt_file, "r")
    for task in f:
        is_prioritized = False
        words = task.split()
        if words and words[0].startswith("("):
            is_prioritized = True
        for word in words:
            if is_word_project(word) and is_prioritized:
                if word not in project_prioritized:
                    project_prioritized[word] = [task]
                else:
                    project_prioritized[word].append(task)
    f.close()
    for event in events:
        words = get_event_words(event)
        for word in words:
            if is_word_project(word):
                if word not in project_prioritized:
                    project_prioritized[word] = [format_event(event, word)]
                else:
                    project_prioritized[word].append(format_event(event, word))
    return project_prioritized

def cross_check_projects(projects, goal_projects):
    cross_check = ''
    for project in projects:
        goal_in_project = False
        for goal in goal_projects:
            if project in goal_projects[goal]:
                goal_in_project = True
        if goal_in_project == False:
            cross_check = cross_check + br("WARNING: Project " + project + " not in goal.")
    return cross_check

def get_gcal_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_gcal(number_days_ago, should_get_past_events=True):
    """Adapted from https://developers.google.com/google-apps/calendar/quickstart/python
    """
    credentials = get_gcal_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    if (should_get_past_events):
        date_n_days_ago = datetime.datetime.now() - timedelta(days=number_days_ago)
    else: # future events
        date_n_days_ago = datetime.datetime.now() + timedelta(days=number_days_ago)

    n_days_ago_iso = date_n_days_ago.isoformat()

    if (should_get_past_events):
        eventsResult = service.events().list(
            calendarId='primary', timeMin=n_days_ago_iso[0:10]+'T00:00:00-04:00', timeMax=time.strftime("%Y-%m-%d")+'T23:59:59-04:00', singleEvents=True,
            orderBy='startTime').execute()
    else:
        eventsResult = service.events().list(
            calendarId='primary', timeMin=time.strftime("%Y-%m-%d")+'T23:59:59-04:00', timeMax=n_days_ago_iso[0:10]+'T00:00:00-04:00', singleEvents=True,
            orderBy='startTime').execute()

    events = eventsResult.get('items', [])
    return events

if __name__ == "__main__":
    main(sys.argv[1:])

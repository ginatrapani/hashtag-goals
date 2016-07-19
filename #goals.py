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
import StringIO

# From Google's sample code
# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


__version__ = "1.0"
__date__ = "2016/03/17"
__updated__ = "2016/07/02"
__author__ = "Gina Trapani (ginatrapani@gmail.com)"
__copyright__ = "Copyright 2016, Gina Trapani"
__license__ = "GPL"
__history__ = """
1.0 - Initial version
"""

def usage():
    print("USAGE:  %s [todo.txt] [done.txt] [#goals.txt] [total days]" % (sys.argv[0], ))

def separator(c, r=42):
    sep = ""
    sep = c * r
    return format_line(sep)

def print_hed(text, sep):
    r = len(text)
    return format_line(text) + separator(sep, r)

def print_title(text):
    return print_hed(text, "=")

def print_header_1(text):
    return print_hed(text, "*")

def print_header_2(text):
    return print_hed(text, "-")

def format_line(text):
    if text == "":
        return "\n"
    else:
        return "    " + text + "\n"

def main(argv):
    # make sure you have all your args
    if len(argv) < 4:
       usage()
       sys.exit(2)

    # Get params
    # TODO Check variable typing and show appropriate error messages
    todo_file = argv[0]
    done_file = argv[1]
    projects_file = argv[2]
    # TODO If this arg doesn't exist default to 7 (last week or so)
    number_days_str = argv[3]
    number_days_int = int(number_days_str)

    goal_projects = get_goal_projects(projects_file)

    last_x_days = get_last_x_days(number_days_int)

    last_x_days_of_completions = get_last_x_days_of_completions(done_file, last_x_days)
    last_x_days_of_completions_from_calendar = get_last_x_days_of_completions_from_calendar(get_gcal(number_days_int))
    last_x_days_of_completions.extend(last_x_days_of_completions_from_calendar)

    project_completions = get_project_completions(last_x_days_of_completions)

    goal_completions = get_goal_completions(goal_projects, project_completions)

    # Next week's prioritizations
    project_prioritized = get_project_prioritized_tasks(todo_file);
    upcoming_events = get_gcal(number_days_int, False)
    project_upcoming_events = get_project_upcoming_events(upcoming_events)
    project_prioritized.update(project_upcoming_events)

    total_tasks_prioritized = get_total_prioritized_tasks(todo_file)
    total_tasks_prioritized += get_total_scheduled_project_events(upcoming_events)

    goal_prioritized = get_goal_prioritized(goal_projects, project_prioritized)

    # Write report to buffer: For each item in goal_projects, print the goal, the number of tasks completed,
    #   then each project and the number of tasks completed
    goals_buf = StringIO.StringIO()

    goals_not_moved = []
    goals_moved = []
    goals_not_prioritized = []
    goals_prioritized = []

    most_progressed_project_total = 0
    most_progressed_projects = []

    least_progressed_project_total = None
    least_progressed_projects = []

    for goal in goal_projects:
        total_done = 0
        if goal in goal_completions:
            total_done = len(goal_completions[goal])

        total_prioritized = 0
        if goal in goal_prioritized:
            total_prioritized = len(goal_prioritized[goal])

        goal_header = goal[3:] + " - " + str(total_done) + " done, " + str(total_prioritized) + " prioritized"
        goals_buf.write(print_title(goal_header))

        if total_done > 0:
            goals_buf.write(format_line(""))
            goals_buf.write(format_line("Completed:"))
        for project in goal_projects[goal]:
            if project in project_completions:
                for task in project_completions[project]:
                    goals_buf.write(format_line(task.strip()))
        if total_done > 0:
            goals_moved.append(goal)
            if total_done > most_progressed_project_total:
                most_progressed_project_total = total_done
            if least_progressed_project_total is None:
                least_progressed_project_total = total_done
            else:
                if total_done < least_progressed_project_total:
                    least_progressed_project_total = total_done
        else:
            goals_buf.write(format_line("No completed tasks."))
            goals_not_moved.append(goal)

        if total_prioritized > 0:
            goals_buf.write(format_line(""))
            goals_buf.write(format_line("Prioritized:"))
            for project in goal_projects[goal]:
                if project in project_prioritized:
                    goals_buf.write(format_line(project))
                    for task in project_prioritized[project]:
                        goals_buf.write(format_line("    " + task.strip()))
            goals_prioritized.append(goal)
            goals_buf.write(format_line(""))
        else:
            goals_buf.write(format_line("No prioritized tasks."))
            goals_not_prioritized.append(goal)

    # Check for multiple most and least progressed goals
    for goal in goal_projects:
        total_done = 0
        if goal in goal_completions:
            total_done = len(goal_completions[goal])
            if total_done == most_progressed_project_total:
                most_progressed_projects.append(goal[3:])
            if total_done == least_progressed_project_total:
                least_progressed_projects.append(goal[3:])

    # Write summary buffer
    summary_buf = StringIO.StringIO()
    summary_buf.write(print_header_2("Summary"))
    summary_buf.write(format_line(str(len(last_x_days_of_completions)) + " completed tasks moved " +
        str(len(goals_moved)) + " out of " + str(len(goal_projects)) + " goals forward."))
    summary_buf.write(format_line(str(total_tasks_prioritized) + " tasks are prioritized which will move " +
        str(len(goals_prioritized)) + " out of " + str(len(goal_projects)) + " goals forward."))
    summary_buf.write(format_line('Made the most progress on ' +
        ('%s' % ' & '.join(map(str, most_progressed_projects))) +
        ' and the least on ' + ('%s' % ' & '.join(map(str, least_progressed_projects)))))
    summary_buf.write(format_line(""))
    # Write list of goals that had no movement
    if len(goals_not_moved) > 0:
        summary_buf.write(format_line("Goals with no progress:"))
        for goal in goals_not_moved:
            summary_buf.write(format_line("    " + goal[3:]))
    # Write list of goals that are not prioritized
    if len(goals_not_prioritized) > 0:
        summary_buf.write(format_line("Goals that are not prioritized:"))
        for goal in goals_not_prioritized:
            summary_buf.write(format_line("    " + goal[3:]))

    # Warnings
    warnings_buf = StringIO.StringIO()
    # Completed project warnings
    warnings_buf.write(cross_check_projects(project_completions, goal_projects))
    # Prioritized project warnings
    warnings_buf.write(cross_check_projects(project_prioritized, goal_projects))

    # Output report
    # Title
    print(format_line("Goal Review for the past " + number_days_str + " days"))
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
        words = event['summary'].split()
        for word in words:
            if word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+":
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
def get_goal_projects(projects_file):
    try:
        goal_projects = {}
        f = open (projects_file, "r")
        for line in f:
            words = line.split()
            for word in words:
                # Project
                if word[0:1] == "+":
                    current_project = word
                # Goal
                if word[0:1] == "#":
                    if word not in goal_projects:
                        goal_projects[word] = [current_project];
                    else:
                        goal_projects[word].append(current_project)
        f.close()
        goal_projects_ordered = collections.OrderedDict(sorted(goal_projects.items()))
        return goal_projects_ordered
    except IOError:
        print(format_line("ERROR:  The file named %s could not be read."% (projects_file, )))
        usage()
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
        print(format_line("ERROR:  The file named %s could not be read."% (done_file, )))
        usage()
        sys.exit(2)

# Return last x days of calendar events with project notations (tasks that were scheduled and completed).
def get_last_x_days_of_completions_from_calendar(events):
    last_x_days_of_completions = []
    for event in events:
        words = event['summary'].split()
        for word in words:
            if word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+":
                last_x_days_of_completions.append(event['summary'])
    return last_x_days_of_completions

# Return an array of projects with their associated tasks.
def get_project_completions(last_x_days_of_completions):
    project_completions = {}
    for task in last_x_days_of_completions:
        words = task.split()
        for word in words:
            if word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+":
                if word not in project_completions:
                    project_completions[word] = [task]
                else:
                    project_completions[word].append(task)
    return project_completions

# Return an array of projects with their associated tasks.
def get_project_prioritized_tasks(todotxt_file):
    project_prioritized = {}
    f = open (todotxt_file, "r")
    for task in f:
        is_prioritized = False
        words = task.split()
        if words and words[0].startswith("("):
            is_prioritized = True
        for word in words:
            if (word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+") and is_prioritized:
                if word not in project_prioritized:
                    project_prioritized[word] = [task]
                else:
                    project_prioritized[word].append(task)
    f.close()
    return project_prioritized

# Return an array of projects with their associated upcoming events.
def get_project_upcoming_events(events):
    project_prioritized = {}
    for event in events:
        words = event['summary'].split()
        for word in words:
            if (word[0:2] == "p:" or word[0:2] == "p-" or word[0:1] == "+"):
                if word not in project_prioritized:
                    project_prioritized[word] = [event['summary']]
                else:
                    project_prioritized[word].append(event['summary'])
    return project_prioritized

def cross_check_projects(projects, goal_projects):
    for project in projects:
        goal_in_project = False
        for goal in goal_projects:
            if project in goal_projects[goal]:
                goal_in_project = True
        if goal_in_project == False:
            return format_line("WARNING: Project " + project + " not in goal.")

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

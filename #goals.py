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

import sys
import datetime
import collections
import StringIO

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
    return formatLine(sep)

def printHed(text, sep):
    r = len(text)
    return formatLine(text) + separator(sep, r)

def printTitle(text):
    return printHed(text, "=")

def printHeader1(text):
    return printHed(text, "*")

def printHeader2(text):
    return printHed(text, "-")

def formatLine(text):
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

    goal_projects = getGoalProjects(projects_file)
    #formatLine(goal_projects)

    last_x_days = getLastXDays(number_days_int)
    #formatLine(last_x_days)

    last_x_days_of_completions = getLastXDaysOfCompletions(done_file, last_x_days)
    #formatLine(last_x_days_of_completions)

    project_completions = getProjectCompletions(last_x_days_of_completions)
    #formatLine(project_completions)

    goal_completions = getGoalCompletions(goal_projects, project_completions)
    # formatLine(goal_completions)

    # Next week's prioritizations
    project_prioritized = getProjectPrioritizedTasks(todo_file);
    # formatLine(project_prioritized)

    total_tasks_prioritized = getTotalPrioritizedTasks(todo_file)

    goal_prioritized = getGoalPrioritized(goal_projects, project_prioritized)
    #formatLine(goal_prioritized)

    # Write report to buffer: For each item in goal_projects, print the goal, the number of tasks completed,
    #   then each project and the number of tasks completed
    goals_buf = StringIO.StringIO()

    goals_not_moved = []
    goals_moved = []
    goals_not_prioritized = []
    goals_prioritized = []

    for goal in goal_projects:
        total_done = 0
        if goal in goal_completions:
            total_done = len(goal_completions[goal])

        total_prioritized = 0
        if goal in goal_prioritized:
            total_prioritized = len(goal_prioritized[goal])

        goal_header = goal[3:] + " - " + str(total_done) + " done, " + str(total_prioritized) + " prioritized"
        goals_buf.write(printTitle(goal_header))

        if total_done > 0:
            goals_buf.write(formatLine(""))
            goals_buf.write(formatLine("Completed:"))
        for project in goal_projects[goal]:
            if project in project_completions:
                for task in project_completions[project]:
                    goals_buf.write(formatLine(task.strip()))
        if total_done > 0:
            goals_moved.append(goal)
        else:
            goals_buf.write(formatLine("No completed tasks."))
            goals_not_moved.append(goal)

        if total_prioritized > 0:
            goals_buf.write(formatLine(""))
            goals_buf.write(formatLine("Prioritized:"))
            for project in goal_projects[goal]:
                if project in project_prioritized:
                    goals_buf.write(formatLine(project))
                    for task in project_prioritized[project]:
                        goals_buf.write(formatLine("    " + task.strip()))
            goals_prioritized.append(goal)
            goals_buf.write(formatLine(""))
        else:
            goals_buf.write(formatLine("No prioritized tasks."))
            goals_not_prioritized.append(goal)

    # Write summary buffer
    summary_buf = StringIO.StringIO()
    summary_buf.write(printHeader2("Summary"))
    summary_buf.write(formatLine(str(len(last_x_days_of_completions)) + " completed tasks moved " +
        str(len(goals_moved)) + " out of " + str(len(goal_projects)) + " goals forward."))
    summary_buf.write(formatLine(str(total_tasks_prioritized) + " tasks are prioritized which will move " +
        str(len(goals_prioritized)) + " out of " + str(len(goal_projects)) + " goals forward."))
    summary_buf.write(formatLine(""))
    # Write list of goals that had no movement
    if len(goals_not_moved) > 0:
        summary_buf.write(formatLine("Goals with no progress:"))
        for goal in goals_not_moved:
            summary_buf.write(formatLine("    " + goal[3:]))
    # Write list of goals that are not prioritized
    if len(goals_not_prioritized) > 0:
        summary_buf.write(formatLine("Goals that are not prioritized:"))
        for goal in goals_not_prioritized:
            summary_buf.write(formatLine("    " + goal[3:]))

    # Warnings
    warnings_buf = StringIO.StringIO()
    # Completed project warnings
    warnings_buf.write(crossCheckProjects(project_completions, goal_projects))
    # Prioritized project warnings
    warnings_buf.write(crossCheckProjects(project_prioritized, goal_projects))

    # Output report
    # Title
    print(formatLine("Goal Review for the past " + number_days_str + " days"))
    # Summary
    print summary_buf.getvalue()
    summary_buf.close()
    # Goals
    print goals_buf.getvalue()
    goals_buf.close()
    # Warnings
    print warnings_buf.getvalue()
    warnings_buf.close()


def getTotalPrioritizedTasks(todotxt_file):
    total = 0
    f = open (todotxt_file, "r")
    for task in f:
        words = task.split()
        if words and words[0].startswith("("):
            total += 1
    f.close()
    return total

# Return an array of goals with total tasks completed.
def getGoalCompletions(goal_projects, project_completions):
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
def getGoalPrioritized(goal_projects, project_prioritized):
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
def getGoalProjects(projects_file):
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
        print(formatLine("ERROR:  The file named %s could not be read."% (projects_file, )))
        usage()
        sys.exit(2)

# Get the last X days as an array of todo.txt-formatted dates.
def getLastXDays(number_days):
    today = datetime.date.today()
    last7Days = []
    for d in range(number_days):
        day_this_week = today - datetime.timedelta(days=d)
        last7Days.append(day_this_week.strftime('%Y-%m-%d'))
    return last7Days

# Return last 7 days of completed tasks from done.txt
def getLastXDaysOfCompletions(done_file, last_x_days):
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
        print(formatLine("ERROR:  The file named %s could not be read."% (done_file, )))
        usage()
        sys.exit(2)

# Return an array of projects with their associated tasks.
def getProjectCompletions(last_x_days_of_completions):
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
def getProjectPrioritizedTasks(todotxt_file):
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

def crossCheckProjects(projects, goal_projects):
    for project in projects:
        goal_in_project = False
        for goal in goal_projects:
            if project in goal_projects[goal]:
                goal_in_project = True
        if goal_in_project == False:
            return formatLine("WARNING: Project " + project + " not in goal.")

if __name__ == "__main__":
    main(sys.argv[1:])

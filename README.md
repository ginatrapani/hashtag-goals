# #goals.py

A goal progress reporter for todo.txt users who do a weekly (or less often) review of tasks and projects.

## Usage
    python \#goals.py [todo.txt] [done.txt] [#goals.txt]

The #goals.py script expects four parameters:

1. A properly-formatted todo.txt file. See [todotxt.com](http://todotxt.com).
2. A properly-formatted done.txt file. See [todotxt.com](http://todotxt.com).
3. A #goals.txt file which lists one #goal followed by any number of +projects associated with it per line.
4. The number of days you want to review. Defaults to 7 for a weekly review.

## Output

Displays a textual report that totals how many tasks you completed associated with a goal categorized by project in the past X days.

## Work in progress

Doesn't quite function as described just yet. See the issue tracker for details on work in progress.

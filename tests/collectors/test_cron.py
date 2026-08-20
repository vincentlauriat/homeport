from homeport.collectors import cron

SYSTEM_CRONTAB = """\
# /etc/crontab: system-wide crontab
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Example of job definition:
17 *	* * *	root	cd / && run-parts --report /etc/cron.hourly
25 6	* * *	root	test -x /usr/sbin/anacron || { cd / && run-parts --report /etc/cron.daily; }
#
"""

CRON_D_FILE = """\
30 3 * * 0 root test -e /run/systemd/system || SERVICE_MODE=1 /usr/libexec/e2fsprogs/e2scrub_all_cron
10 3 * * * root test -e /run/systemd/system || SERVICE_MODE=1 /sbin/e2scrub_all -A -r
"""


def test_parse_crontab_skips_comments_and_blank_lines():
    jobs = cron.parse_crontab("# a comment\n\n" + SYSTEM_CRONTAB)

    assert len(jobs) == 2


def test_parse_crontab_skips_variable_assignments():
    jobs = cron.parse_crontab("SHELL=/bin/sh\nPATH=/usr/bin\n")

    assert jobs == []


def test_parse_crontab_extracts_schedule_user_and_command():
    jobs = cron.parse_crontab(CRON_D_FILE)

    assert jobs[0] == {
        "schedule": "30 3 * * 0",
        "user": "root",
        "command": "test -e /run/systemd/system || SERVICE_MODE=1 /usr/libexec/e2fsprogs/e2scrub_all_cron",
    }


def test_parse_crontab_handles_tabs_and_spaces_as_separators():
    jobs = cron.parse_crontab(SYSTEM_CRONTAB)

    assert jobs[0] == {
        "schedule": "17 * * * *",
        "user": "root",
        "command": "cd / && run-parts --report /etc/cron.hourly",
    }

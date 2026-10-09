---
name: "cron"
description: "Read and install a user crontab without deleting the jobs already there. Use when a command needs to run on a schedule."
---

# Cron

Schedule a command in the user's crontab. Read what is already there, add one line, check the syntax, then install the whole file.

## When to use

A command should run later on a clock: every night, once an hour, or at a fixed minute. This skill edits the user crontab for the account you are logged in as.

## Install

```sh
command -v crontab
```

Debian and Ubuntu ship crontab in the `cron` package. The daemon has to be running or the table never fires.

```sh
sudo apt-get install cron
sudo service cron start
service cron status
```

macOS includes `crontab`. The system scheduler there is launchd; use this skill only when the user asked for cron.

## Commands

A user crontab line is five time fields and then the command:

```text
minute  hour  day-of-month  month  day-of-week  command
```

Minute `0-59`, hour `0-23`, day of month `1-31`, month `1-12`, day of week `0-7` (`0` and `7` are Sunday). `*` means every value.

Save the current table first. A missing crontab makes `crontab -l` exit non-zero and write nothing; that empty backup is the right start.

```sh
crontab -l > "$HOME/crontab.backup" || true
```

If stderr says something other than "no crontab", stop. Do not install a new file over a table you could not read.

Add one job onto the end of that backup. Use absolute paths. Cron's `PATH` is short, and the shell is `/bin/sh`. Send both stdout and stderr to a log you can read later.

```sh
cp "$HOME/crontab.backup" jobs.cron
printf '%s\n' '15 3 * * * /usr/bin/python3 /home/me/jobs/backup.py >> /home/me/logs/backup.log 2>&1' >> jobs.cron
```

On Debian and Ubuntu, `-n` checks the file and does not install it:

```sh
crontab -n jobs.cron
```

Install, then list. Confirm the old lines are still there and the new line was added.

```sh
crontab jobs.cron
crontab -l
```

Useful shortcuts on Vixie cron (Debian, cronie): `@hourly`, `@daily`, `@weekly`, `@monthly`, `@reboot`. They replace the five time fields.

## Gotchas

- `crontab jobs.cron` replaces the entire user crontab with that file. The backup step is what keeps the previous jobs.
- `crontab -r` deletes every job. Do not run it.
- A `%` in the command becomes a newline, and the rest of the line is fed to the command as stdin. Write a literal percent as `\%`.
- If both the day-of-month and day-of-week fields are restricted (neither is `*`), cron runs the job when either field matches.
- Jobs do not see your interactive `PATH`. The example uses `/usr/bin/python3` and an absolute script path for that reason.
- Output with nowhere to go is mailed to the crontab owner. The `>> log 2>&1` redirect keeps it in a file. Create the log directory first; the redirect does not create parent directories.
- Replace `/home/me` in the example with the real home directory before installing.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)

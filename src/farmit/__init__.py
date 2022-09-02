#!/usr/bin/env python
"""Fully Automated Release Management tool.

Creates and pushes a release branch off the default branch containing
a commit with updates to the CHANGELOG.md file. The change information
is collected from commits since the last tag. Commits are expected
to have a title line followed by lines formatted as a markdown list:

    Title line

    * Description 1
    * Description 2

    Fixes #1234

This example commit will appear as below in the CHANGELOG.md and
the release commit. Note that empty lines and lines containing
GitHub keywords, such as fixes, are removed:

+ Title line
  * Description 1
  * Description 2

Examples:
    farm micro
    farm 3.0.0
"""

import argparse
import logging
import os
import re
import sys
import traceback

from argparse import Namespace
from io import StringIO
from typing import List, Optional, Tuple

from git import Head, Repo, Remote
from git.exc import GitCommandError
from pydriller import Repository
from pydriller.domain.commit import Commit
from setuptools_scm import Version, get_version

logger = logging.getLogger("__name__")

BRANCH_CHANGED = False  # Have we changed branches?


def log_setup(args):
    global LOG_CAPTURE
    global STDOUT_HANDLER
    global STDERR_HANDLER
    global DEBUG_HANDLER

    LOG_CAPTURE = StringIO()
    logger.setLevel(logging.DEBUG)

    # INFO and below goes to stdout
    STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
    if args.verbose:
        STDOUT_HANDLER.setLevel(logging.DEBUG)
    else:
        STDOUT_HANDLER.setLevel(logging.WARN)
    STDOUT_HANDLER.addFilter(lambda record: record.levelno <= logging.INFO)
    logger.addHandler(STDOUT_HANDLER)

    # WARN and above goes to stderr
    STDERR_HANDLER = logging.StreamHandler(sys.stderr)
    STDERR_HANDLER.setLevel(logging.WARNING)
    logger.addHandler(STDERR_HANDLER)

    # Save all logs in string object
    DEBUG_HANDLER = logging.StreamHandler(LOG_CAPTURE)
    DEBUG_HANDLER.setLevel(logging.DEBUG)
    logger.addHandler(DEBUG_HANDLER)


def _easter_egg():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        "--darn-it",
        action="store_true",
        help=argparse.SUPPRESS)

    args, _ = parser.parse_known_args()

    if args.darn_it:
        print("""
                           _.-^-._    .--.
                        .-'   _   '-. |__|
                       /     |_|     \\|  |
                      /               \\  |
                     /|     _____     |\\ |
                      |    |==|==|    |  |
  |---|---|---|---|---|    |--|--|    |  |
  |---|---|---|---|---|    |==|==|    |  |
 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
""")
        sys.exit(0)

    return parser


def init_parser(parser):
    parser.add_argument(
        "release",
        help="Release type (major, minor, micro) or version tag"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action='store_true',
        help="Do a dry-run without making changes")
    parser.add_argument(
        "-r",
        "--remote",
        type=str,
        default='origin',
        help="Remote to branch off and push to")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output")
    parser.add_argument(
        "-u",
        "--allow-uncommited-changes",
        action="store_true",
        help="Allow farm to run with uncommited changes"),
    return parser


class FarmError(Exception):
    pass


class NotGitRepoError(FarmError):
    def __init__(self):
        super().__init__(
            "fatal: not a git repository "
            "(or any of the parent directories): .git"
        )


class DirtyRepoError(FarmError):
    def __init__(self):
        super().__init__("fatal: uncommitted changes")


class UntrackedFilesError(FarmError):
    def __init__(self):
        super().__init__("fatal: untracked files")


def error(*args, **kwargs):
    """Drop in replacement for print that prints to stderr."""
    kwargs['file'] = sys.stderr
    kwargs['flush'] = True
    print(*args, **kwargs)


def unknown_error(e):
    """Dump all logs and traceback to stderr."""
    error(LOG_CAPTURE.getvalue(), end='')
    error(traceback.format_exc())


def build_changelog_entries(version: str, commits: List[Commit]
                            ) -> Tuple[str, str]:
    """Returns release changelog markdown header & list of changes"""
    header = f"## {version}\n"
    body = ""

    for commit in commits:
        body += f"{build_message(commit)}\n"

    return header, body


def build_message(commit: Commit) -> str:
    """Return changelog entry for a single commit"""
    keywords = r'fix(es|ed)|close(s|d)|resolve(s|d)|address(es|ed)|part of'
    regex = r'(?im)^\s*(' + keywords + r')\s*#\d+$|^Co-authored-by.*$'

    # Convert commit message to List(str) & remove lines w/GitHub Keywords
    commit_msg = re.sub(regex, '', commit.msg).split('\n')
    # Remove empty lines and whitespace
    commit_msg = [x.strip() for x in commit_msg if x.strip()]

    # Append '+ ' to commit title
    title = ['+ ' + commit_msg[0]]
    # Indent commit message by two spaces
    description = [f'  {x}' for x in commit_msg[1:]]

    return '\n'.join(title + description)


def get_next_release(args: Namespace, last_release: Optional[str]) -> str:
    """Returns next release version strings"""

    if not last_release:
        version = Version('0.0.0')
    else:
        version = Version(last_release)

    major = version.major
    minor = version.minor
    micro = version.micro

    if args.release == 'major':
        next_release = f"{major+1}.0.0"
    elif args.release == 'minor':
        next_release = f"{major}.{minor+1}.0"
    elif args.release == 'micro':
        next_release = f"{major}.{minor}.{micro+1}"
    else:
        next_release = args.release

    return next_release


def update_changelog(args: Namespace, changelog_path: str, entry: str):
    """Prepend entry to changelog_path"""
    try:
        with open(changelog_path, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        content = b''
        logger.warning(
            "WARNING: Creating CHANGELOG.md since it does not exist"
        )

    if entry.split('\n')[0].encode('utf8') not in content:
        # Without 'b', on Windows, \n is converted to \r\n
        with open(changelog_path, 'wb') as f:
            f.write(entry.encode('utf8'))
            f.write(content)

        logger.info("Updated CHANGELOG.md:")
        logger.info(entry)
    else:
        logger.warning("CHANGELOG.md is already up-to-date")


def get_current_release(repo: Repo) -> Optional[str]:
    """Return the current release tag.
    If no release tags exist None is returned."""

    if not repo.tags:
        return None

    # Version returns next micro release
    next = Version(get_version().split('.dev'))
    return f"{next.major}.{next.minor}.{next.micro-1}"


def main(args: Namespace, repo: Repo):
    remote = repo.remote(args.remote)

    current_release = get_current_release(repo)
    version = get_next_release(args, current_release)

    branch = create_release_branch(args, repo, remote, version)

    # Retrieve unreleased commits
    # BUG: The order is NOT deterministic :-(
    unreleased_commits = list(Repository(
        repo.working_tree_dir,
        from_tag=current_release,
        order='reverse',
    ).traverse_commits())
    del unreleased_commits[-1]

    # Build changelog entry
    title, body = build_changelog_entries(version, unreleased_commits)
    entry = f"{title}\n{body}\n"

    changelog_path = os.path.join(str(repo.working_tree_dir), 'CHANGELOG.md')
    if args.dry_run:
        print("If not run with --dry-run, farmit would update "
              f"{changelog_path} with:\n{entry}")
    else:
        update_changelog(args, changelog_path, entry)
        commit_push_changelog(args, repo, remote, changelog_path, version,
                              body)
        print_pr_url(remote, branch)


def commit_push_changelog(args: Namespace, repo: Repo, remote: Remote,
                          path: str, version: str, body: str):
    """Commit CHANGELOG.md and push release branch to remote"""
    branch = repo.active_branch

    repo.index.add(path)
    if repo.is_dirty():
        repo.index.commit(f'Release {version}\n\n{body}')
        logger.info("Commited CHANGELOG.md on release branch")
    else:
        logger.warning("CHANGELOG.md has already been commited")

    if repo.git.status(s=True) or not branch.tracking_branch():
        remote.push(branch)
        logger.info("Pushed release branch")

        if not branch.tracking_branch():
            branch.set_tracking_branch(remote.refs[branch.name])
            logger.info(f"Tracking branch set: {remote.refs[branch.name]}")
        else:
            logger.warning("Tracking branch has already been set")
    else:
        logger.warning("Release branch has already been pushed")


def parse_remote_url(remote: Remote) -> Tuple[str, List[str]]:
    """Return remote url scheme as a string and path as a list."""
    url_split = remote.url.split(':')
    scheme, path = url_split[0], ':'.join(url_split[1:])

    return scheme, (path[:-4] if path.endswith('.git') else path).split('/')


def print_pr_url(remote: Remote, branch: Head):
    """Print a url for creating a PR if origin is on GitHub"""
    scheme, path = parse_remote_url(remote)

    if 'git@github.com' == scheme or \
       (len(path) > 1 and path[2] == 'github.com'):
        br, org, repo = (branch.name, path[-2], path[-1])

        print(
            f"Create a pull request for '{br}' on GitHub by visiting:\n"
            f"\thttps://github.com/{org}/{repo}/pull/new/{br}"
        )


def create_release_branch(args: Namespace, repo: Repo, remote: Remote,
                          version: Optional[str]) -> Head:
    """Create & checkout release branch off updated default branch"""
    global BRANCH_CHANGED
    branch_name = f"release/{version}"

    # Update repo & determine origin's default branch (master/main)
    remote.fetch()
    default_branch = remote.refs['HEAD'].ref.name

    try:
        # Create release branch directly off origin's default branch
        branch = repo.create_head(branch_name, default_branch)
        logger.info(
            f"Created release branch {branch_name} from {default_branch}"
        )
    except OSError:
        branch = repo.branches[branch_name]
        logger.warn(f"Release branch {branch_name} already exists")

    branch.checkout()
    BRANCH_CHANGED = True
    logger.info(f"Checked out release branch: {branch_name}")

    return branch


def _main(user_args=None):
    args = init_parser(_easter_egg()).parse_args(user_args)
    log_setup(args)
    code = 0

    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)

        if repo.bare:
            raise NotGitRepoError
        if not args.allow_uncommited_changes and repo.is_dirty():
            raise DirtyRepoError
        if repo.untracked_files:
            raise UntrackedFilesError

        main(args, repo)
    except FarmError as e:
        error(e)
        code = 1
    except Exception as e:
        unknown_error(e)
        code = 2
    finally:
        try:
            if BRANCH_CHANGED:
                repo.git.checkout('-')
        except GitCommandError as e:
            error(e)
        except Exception as e:
            unknown_error(e)

        logging.shutdown()

    sys.exit(code)


if __name__ == "__main__":
    _main()

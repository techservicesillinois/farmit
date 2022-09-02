from argparse import Namespace
import os
import datetime

import farmit
import pytest

from pathlib import Path

from git import Repo


def commit(repo: Repo, path: Path, file_content: str, commit_message: str,
           date: str):
    """Create a file & commit it."""
    date = datetime.date(*date).strftime('%Y-%m-%d %H:%M:%S')

    path = Path(repo.working_tree_dir) / path
    with open(path, 'wb') as new_file:
        # 'wb' and 'encode' force unix line endings on Windows
        new_file.write(file_content.encode('utf8'))
    repo.index.add(str(path))
    return repo.index.commit(commit_message, author_date=date,
                             commit_date=date)


@pytest.fixture
def remote_url(tmp_path):
    """Returns the remote url of an empty bare git repository."""
    repo_path = tmp_path / "origin"
    repo_path.mkdir()
    Repo.init(repo_path, bare=True)
    return f'file://{str(repo_path)}'


def build_repo(repo_path, remote_url, include_tag=True) -> Repo:
    """Populates a Git repository.
    
    If called with include_tag=False, no tag is created.
    """

    repo = Repo.init(repo_path)
    today = (1970, 5, 29)
    if include_tag:
        commit(repo, "CHANGELOG.md", "## 1.0.0\n\n+ Initial Release",
            'Release 1.0.0', today)
    else:
        commit(repo, "README.md", "Awesome repo", '1st commit', today)

    repo.create_remote('origin', url=remote_url)
    if include_tag:
        repo.create_tag('1.0.0')
    repo.git.push('--set-upstream', 'origin', 'master')
    repo.git.push('--tags')
    repo.git.remote('set-head', 'origin', '-a')

    os.chdir(str(repo_path))
    return repo


@pytest.fixture
def repo(tmp_path, remote_url, request):
    """Returns a Git repository with one commit & tag.

    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    yield build_repo(repo_path, remote_url, True)
    os.chdir(request.config.invocation_dir)


@pytest.fixture
def no_tags_repo(tmp_path, remote_url, request):
    """Returns a Git repository with one commit & no tags."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    yield build_repo(repo_path, remote_url, False)
    os.chdir(request.config.invocation_dir)


@pytest.mark.parametrize("date1, date2, emesg", [
    # Try day before & after first commit to make sure commits are
    # NOT sorted by date but by chronological order of insertion
    # https://git-scm.com/docs/git-rev-list#_commit_ordering
    #
    # TODO: File a new bug report against PyDriller. It appears that #106
    # should have solved this bug.
    pytest.param(
        (1970, 5, 28), (1970, 5, 27), "Commits dated before first commit",
        marks=pytest.mark.xfail(reason="Due to a bug in PyDriller #93, #94")
    ),
    ((1970, 5, 30), (1970, 5, 31), "Commits dated after first commit"),
])
def test_basic(capsys, repo, date1, date2, emesg):
    commit(repo, 'main.py', 'import sys', 'First commit', date1)
    commit(repo, 'test.py', 'import pytest', 'Second commit', date2)
    repo.git.push()

    excinfo = pytest.raises(SystemExit, farmit._main, ['micro'])
    out, error = capsys.readouterr()

    assert excinfo.value.code == 0, error
    assert repo.active_branch.name == 'master'
    assert 'release/1.0.1' in repo.branches

    release_branch = repo.branches['release/1.0.1'].commit
    assert release_branch.message == \
        "Release 1.0.1\n\n+ Second commit\n+ First commit\n", emesg
    assert release_branch.parents[0] == repo.commit('master')

    diff = release_branch.diff('master')
    assert len(diff) == 1
    assert diff[0].change_type == 'M'
    assert diff[0].a_rawpath == b'CHANGELOG.md'
    assert diff[0].a_blob.data_stream.read() == \
        b'## 1.0.1\n\n+ Second commit\n+ First commit\n\n' \
        b'## 1.0.0\n\n+ Initial Release'
    assert diff[0].b_rawpath == b'CHANGELOG.md'
    assert diff[0].b_blob.data_stream.read() == \
        b'## 1.0.0\n\n+ Initial Release'


def test_strip_normalize_newlines(repo):
    """Regression test for issue #4."""
    # farmit should remove leading & trailing whitespace
    commit(repo, 'main.py', 'foo', '\t1st commit\t\n\n', (1970, 5, 30))
    # farmit should normilize line endings to Unix style
    commit(repo, 'test.py', 'bar', ' 2nd commit \r\n', (1970, 5, 31))
    repo.git.push()

    pytest.raises(SystemExit, farmit._main, ['minor'])

    # Check contents of commit message
    release_branch = repo.branches['release/1.1.0'].commit
    assert release_branch.message == \
        "Release 1.1.0\n\n+ 2nd commit\n+ 1st commit\n"

    # Checking contents of CHANGELOG.md
    diff = release_branch.diff('master')
    assert diff[0].a_blob.data_stream.read() == \
        b'## 1.1.0\n\n+ 2nd commit\n+ 1st commit\n\n' \
        b'## 1.0.0\n\n+ Initial Release'


@pytest.mark.parametrize("mesg, output, error", [
    (' commit \r\n', '+ commit', 'Whitespace remains'),
    ('commit\nFixes #18', '+ commit', 'Fixes line remains'),
    ('commit\nCo-authored-by: tstark', '+ commit', 'Coauthors remain'),
])
def test_build_message(mesg, output, error):
    commit = Namespace()
    commit.msg = mesg

    assert output == farmit.build_message(commit), error


def test_version_increase(repo, capsys):
    """Regression test for issue #5."""
    commit(repo, 'main.py', 'foo', 'Release 1.0.9', (1970, 5, 30))
    repo.create_tag('1.0.9')
    commit(repo, 'test.py', 'bar', 'Release 1.0.10', (1970, 5, 31))
    repo.create_tag('1.0.10')
    commit(repo, 'test.py', 'bar', '1st commit', (1970, 6, 1))
    repo.git.push('--tags')
    repo.git.push()

    excinfo = pytest.raises(SystemExit, farmit._main, ['micro'])
    out, error = capsys.readouterr()

    assert excinfo.value.code == 0, error
    assert set(['release/1.0.11', 'master']) == \
        set([branch.name for branch in repo.branches])
    assert repo.branches['release/1.0.11'].commit.message == \
        "Release 1.0.11\n\n+ 1st commit\n"


@pytest.mark.parametrize("version, expected, args", [
    ('1.1.0', '1.1.1', ['micro', '--dry-run']),
    ('1.1.0', '1.2.0', ['minor', '--dry-run']),
    ('1.1.0', '2.0.0', ['major', '--dry-run']),
    ('1.1.0', '9.8.9', ['9.8.9', '--dry-run']),
])
def test_get_next_release(version, expected, args):

    parsed_args = farmit.init_parser(farmit._easter_egg()).parse_args(args)
    next = farmit.get_next_release(parsed_args, version)
    assert next == expected


def test_get_no_current_release(no_tags_repo):
    assert farmit.get_current_release(no_tags_repo) == None

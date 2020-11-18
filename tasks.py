"""
Tasks for maintaining the project.

Execute 'invoke --list' for guidance on using Invoke
"""
import os
import glob
import shutil
import platform

from invoke import task
from pathlib import Path
import webbrowser


MAX_LINE_LENGTH = 88

ROOT_DIR = Path(__file__).parent
SETUP_FILE = ROOT_DIR.joinpath("setup.py")
TEST_DIR = ROOT_DIR.joinpath("tests")
SOURCE_DIR = ROOT_DIR.joinpath("modularyze")
TOX_DIR = ROOT_DIR.joinpath(".tox")
COVERAGE_FILE = ROOT_DIR.joinpath(".coverage")
COVERAGE_DIR = ROOT_DIR.joinpath("htmlcov")
COVERAGE_REPORT = COVERAGE_DIR.joinpath("index.html")
DOCS_DIR = ROOT_DIR.joinpath("docs")
DOCS_BUILD_DIR = DOCS_DIR.joinpath("_build")
DOCS_INDEX = DOCS_BUILD_DIR.joinpath("index.html")
PYTHON_DIRS = [str(d) for d in [SOURCE_DIR, TEST_DIR]]


def _delete_file(file):
    if os.path.isfile(file):
        print(f"Removing file {file}...")
        os.remove(file)
    elif os.path.isdir(file):
        print(f"Removing directory {file}...")
        shutil.rmtree(file, ignore_errors=True)


def _delete_pattern(pattern):
    for file in glob.glob(os.path.join("**", pattern), recursive=True):
        _delete_file(file)


def _run(c, command):
    return c.run(command, pty=platform.system() != "Windows")


@task(help={"check": "Checks if source is formatted without applying changes"})
def format(c, check=False):
    """Format code"""
    python_dirs_string = " ".join(PYTHON_DIRS)
    # Run isort
    isort_options = f'--line-length={MAX_LINE_LENGTH}' + ' --check-only --diff' if check else ''
    _run(c, f"isort {isort_options} {python_dirs_string}")
    # Run Black
    yapf_options = "--diff --check" if check else ""
    _run(c, f"black --line-length={MAX_LINE_LENGTH} {yapf_options} {python_dirs_string}")


@task
def lint_flake8(c):
    """Lint code with flake8"""
    _run(c, f"flake8 {' '.join(PYTHON_DIRS)}")


@task
def lint_pylint(c):
    """Lint code with pylint"""
    _run(c, f"pylint --max-line-length={MAX_LINE_LENGTH} {' '.join(PYTHON_DIRS)}")


@task(lint_flake8, lint_pylint)
def lint(c):
    """Run all linting"""


@task
def test(c):
    """Run tests"""
    _run(c, "pytest")


@task(help={"publish": "Publish the result via coveralls"})
def coverage(c, publish=False):
    """Create coverage report"""
    _run(c, f"coverage run --source {SOURCE_DIR} -m pytest")
    _run(c, "coverage report")
    if publish:
        # Publish the results via coveralls
        _run(c, "coveralls")
    else:
        # Build a local report
        _run(c, "coverage html")
        webbrowser.open(COVERAGE_REPORT.as_uri())


@task(help={"launch": "Launch documentation in the web browser"})
def docs(c, launch=True):
    """Generate documentation"""
    _run(c, f"sphinx-build -b html {DOCS_DIR} {DOCS_BUILD_DIR}")
    if launch:
        webbrowser.open(DOCS_INDEX.as_uri())


@task
def clean_docs(c):
    """Clean up files from documentation builds"""
    _delete_file(DOCS_BUILD_DIR)


@task
def clean_build(c):
    """Clean up files from package building"""
    _delete_file("build/")
    _delete_file("dist/")
    _delete_file(".eggs/")
    _delete_pattern("*.egg-info")
    _delete_pattern("*.egg")


@task
def clean_python(c):
    """Clean up python file artifacts"""
    _delete_pattern("__pycache__")
    _delete_pattern("*.pyc")
    _delete_pattern("*.pyo")
    _delete_pattern("*~")


@task
def clean_tests(c):
    """Clean up files from testing"""
    _delete_file(COVERAGE_FILE)
    _delete_file(TOX_DIR)
    _delete_file(COVERAGE_DIR)
    _delete_pattern(".pytest_cache")


@task(pre=[clean_build, clean_python, clean_tests, clean_docs])
def clean(c):
    """Runs all clean sub-tasks"""


@task(clean)
def dist(c):
    """Build source and wheel packages"""
    _run(c, "poetry build")


@task(pre=[clean, dist])
def release(c):
    """Make a release of the python package to pypi"""
    _run(c, "poetry publish")

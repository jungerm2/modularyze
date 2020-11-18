import os

import pytest
from testfixtures import TempDirectory

from modularyze import ConfBuilder


@pytest.fixture()
def tmp_dir():
    with TempDirectory() as tmp_dir:
        yield tmp_dir


def setup_directory(tmp_dir, file_paths, file_contents):
    for file_path, file_content in zip(file_paths or [], file_contents or []):
        tmp_dir.write(file_path, file_content.encode())


@pytest.fixture
def build_from_doc(tmp_dir):
    """Return a configuration object from a document/string"""
    builder = ConfBuilder()
    old_build = builder.build

    def _build_from_doc(doc, file_paths=None, file_contents=None, **kwargs):
        setup_directory(tmp_dir, file_paths, file_contents)
        return old_build(doc, root_path=tmp_dir.path, **kwargs)

    builder.build = _build_from_doc
    return builder


@pytest.fixture
def build_from_file(tmp_dir):
    """Return a configuration object from a mocked file"""
    builder = ConfBuilder()
    old_build = builder.build

    def _build_from_file(
        mock_data, mock_path="main.yaml", file_paths=None, file_contents=None, **kwargs
    ):
        setup_directory(tmp_dir, file_paths, file_contents)
        tmp_dir.write(mock_path, mock_data.encode())
        is_single_file = file_paths is None and file_contents is None
        spec = os.path.join(tmp_dir.path, mock_path) if is_single_file else mock_path
        root_path = None if is_single_file else tmp_dir.path
        return old_build(spec, root_path=root_path, **kwargs)

    builder.build = _build_from_file
    return builder


@pytest.fixture(params=["build_from_doc", "build_from_file"])
def builder(request):
    return request.getfixturevalue(request.param)

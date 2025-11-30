import sys
import os
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Return the test data directory"""
    return os.path.join(project_root, 'tests', 'data')
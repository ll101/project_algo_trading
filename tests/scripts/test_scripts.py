"""
Tests for shell scripts.
These are integration tests that verify script functionality.
"""

import unittest
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


class TestScripts(unittest.TestCase):
    """Test cases for shell scripts."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.scripts_dir = self.project_root / 'scripts'
        self.docker_dir = self.project_root / 'docker'
    
    def test_check_container_script_exists(self):
        """Test that check_container.sh script exists and is executable."""
        script_path = self.scripts_dir / 'check_container.sh'
        self.assertTrue(script_path.exists(), "check_container.sh should exist")
        self.assertTrue(os.access(script_path, os.X_OK), "check_container.sh should be executable")
    
    def test_start_container_script_exists(self):
        """Test that start_container.sh script exists and is executable."""
        script_path = self.scripts_dir / 'start_container.sh'
        self.assertTrue(script_path.exists(), "start_container.sh should exist")
        self.assertTrue(os.access(script_path, os.X_OK), "start_container.sh should be executable")
    
    def test_stop_container_script_exists(self):
        """Test that stop_container.sh script exists and is executable."""
        script_path = self.scripts_dir / 'stop_container.sh'
        self.assertTrue(script_path.exists(), "stop_container.sh should exist")
        self.assertTrue(os.access(script_path, os.X_OK), "stop_container.sh should be executable")
    
    def test_init_database_script_exists(self):
        """Test that init_database.sh script exists and is executable."""
        script_path = self.scripts_dir / 'init_database.sh'
        self.assertTrue(script_path.exists(), "init_database.sh should exist")
        self.assertTrue(os.access(script_path, os.X_OK), "init_database.sh should be executable")
    
    def test_setup_docker_script_exists(self):
        """Test that setup_docker.sh script exists and is executable."""
        script_path = self.scripts_dir / 'setup_docker.sh'
        self.assertTrue(script_path.exists(), "setup_docker.sh should exist")
        self.assertTrue(os.access(script_path, os.X_OK), "setup_docker.sh should be executable")
    
    def test_check_container_script_syntax(self):
        """Test that check_container.sh has valid bash syntax."""
        script_path = self.scripts_dir / 'check_container.sh'
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, 
                        f"Script syntax error: {result.stderr}")
    
    def test_start_container_script_syntax(self):
        """Test that start_container.sh has valid bash syntax."""
        script_path = self.scripts_dir / 'start_container.sh'
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, 
                        f"Script syntax error: {result.stderr}")
    
    def test_stop_container_script_syntax(self):
        """Test that stop_container.sh has valid bash syntax."""
        script_path = self.scripts_dir / 'stop_container.sh'
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, 
                        f"Script syntax error: {result.stderr}")
    
    def test_init_database_script_syntax(self):
        """Test that init_database.sh has valid bash syntax."""
        script_path = self.scripts_dir / 'init_database.sh'
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, 
                        f"Script syntax error: {result.stderr}")
    
    def test_setup_docker_script_syntax(self):
        """Test that setup_docker.sh has valid bash syntax."""
        script_path = self.scripts_dir / 'setup_docker.sh'
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, 
                        f"Script syntax error: {result.stderr}")
    
    def test_docker_compose_file_exists(self):
        """Test that docker-compose.yml exists."""
        compose_file = self.docker_dir / 'docker-compose.yml'
        self.assertTrue(compose_file.exists(), "docker-compose.yml should exist")
    
    def test_init_sql_file_exists(self):
        """Test that init.sql exists."""
        init_sql = self.docker_dir / 'init.sql'
        self.assertTrue(init_sql.exists(), "init.sql should exist")
    
    def test_docker_compose_uses_correct_image(self):
        """Test that docker-compose.yml uses the correct TimescaleDB image."""
        compose_file = self.docker_dir / 'docker-compose.yml'
        content = compose_file.read_text()
        self.assertIn('timescale/timescaledb:latest-pg17', content,
                     "docker-compose.yml should use timescale/timescaledb:latest-pg17")
    
    def test_docker_compose_has_healthcheck(self):
        """Test that docker-compose.yml has a healthcheck configuration."""
        compose_file = self.docker_dir / 'docker-compose.yml'
        content = compose_file.read_text()
        self.assertIn('healthcheck', content,
                     "docker-compose.yml should have a healthcheck")
    
    def test_init_sql_creates_hypertables(self):
        """Test that init.sql creates hypertables."""
        init_sql = self.docker_dir / 'init.sql'
        content = init_sql.read_text()
        self.assertIn('create_hypertable', content,
                     "init.sql should create hypertables")
        self.assertIn('trading.bars', content,
                     "init.sql should create bars hypertable")
        self.assertIn('trading.quotes', content,
                     "init.sql should create quotes hypertable")
        self.assertIn('trading.trades', content,
                     "init.sql should create trades hypertable")


if __name__ == '__main__':
    unittest.main()


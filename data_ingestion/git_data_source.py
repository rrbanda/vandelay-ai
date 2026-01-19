"""
Git Data Source
================

Utility for fetching data files from a git repository URL.

Supports:
- GitHub raw URLs
- GitLab raw URLs
- Generic git clone + file extraction

Usage:
    from data_ingestion.git_data_source import GitDataSource
    
    source = GitDataSource("https://github.com/user/repo.git")
    documents = source.fetch_documents("data/fsi_documents")
    cypher_data = source.fetch_file("data/fsi_sample_data.cypher")
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
import subprocess


class GitDataSource:
    """
    Fetch data files from a git repository.
    
    Can work with:
    - Local directories
    - Git repository URLs (cloned to temp)
    - Raw file URLs (GitHub/GitLab)
    """
    
    def __init__(
        self,
        source: str,
        branch: str = "main",
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the data source.
        
        Args:
            source: Local path or git URL
            branch: Git branch to use (default: main)
            cache_dir: Directory to cache cloned repos
        """
        self.source = source
        self.branch = branch
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix="git_data_")
        self._repo_path: Optional[Path] = None
        self._is_local = self._check_if_local(source)
    
    def _check_if_local(self, source: str) -> bool:
        """Check if source is a local directory."""
        return os.path.isdir(source)
    
    def _clone_repo(self) -> Path:
        """Clone the git repository to cache directory."""
        if self._repo_path and self._repo_path.exists():
            return self._repo_path
        
        repo_name = Path(urlparse(self.source).path).stem or "repo"
        self._repo_path = Path(self.cache_dir) / repo_name
        
        # Remove existing clone
        if self._repo_path.exists():
            shutil.rmtree(self._repo_path)
        
        print(f"Cloning {self.source} (branch: {self.branch})...")
        
        try:
            subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", self.branch,
                    self.source,
                    str(self._repo_path)
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"[ok] Cloned to {self._repo_path}")
        except subprocess.CalledProcessError as e:
            print(f"[error] Failed to clone: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
        
        return self._repo_path
    
    def get_base_path(self) -> Path:
        """Get the base path for the data source."""
        if self._is_local:
            return Path(self.source)
        return self._clone_repo()
    
    def fetch_file(self, relative_path: str) -> str:
        """
        Fetch a single file's content.
        
        Args:
            relative_path: Path relative to repository root
            
        Returns:
            File content as string
        """
        base = self.get_base_path()
        file_path = base / relative_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def fetch_documents(
        self,
        relative_dir: str,
        pattern: str = "*.txt",
    ) -> List[Dict[str, str]]:
        """
        Fetch all documents from a directory.
        
        Args:
            relative_dir: Directory path relative to repository root
            pattern: Glob pattern for files
            
        Returns:
            List of documents with 'name' and 'content' keys
        """
        base = self.get_base_path()
        dir_path = base / relative_dir
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        documents = []
        for file_path in sorted(dir_path.glob(pattern)):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            documents.append({
                'name': file_path.name,
                'content': content,
            })
            print(f"  Loaded: {file_path.name} ({len(content)} chars)")
        
        return documents
    
    def fetch_cypher_file(self, relative_path: str = "data/fsi_sample_data.cypher") -> str:
        """
        Fetch the Cypher sample data file.
        
        Args:
            relative_path: Path to cypher file
            
        Returns:
            Cypher statements as string
        """
        return self.fetch_file(relative_path)
    
    def cleanup(self):
        """Clean up cloned repository."""
        if self._repo_path and self._repo_path.exists() and not self._is_local:
            shutil.rmtree(self._repo_path, ignore_errors=True)
            print(f"[ok] Cleaned up {self._repo_path}")


def get_data_source(
    source_url: Optional[str] = None,
    branch: str = "main",
) -> GitDataSource:
    """
    Get a data source from URL or use local data.
    
    Args:
        source_url: Git repository URL or None to use local data
        branch: Git branch
        
    Returns:
        GitDataSource instance
    """
    if source_url:
        return GitDataSource(source_url, branch=branch)
    
    # Default to local data_ingestion directory (parent of this file)
    # This allows paths like "data/fsi_sample_data.cypher" to work
    local_path = Path(__file__).parent
    return GitDataSource(str(local_path))
